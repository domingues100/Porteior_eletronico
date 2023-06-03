import cv2  
import time
from firebase_admin import credentials, initialize_app, storage, firestore 
import os 
import pyrebase
import face_recognition
from datetime import datetime
import threading

encodings = {}
encodings_names = []

#configs
config = {
    "apiKey": "AIzaSyBfUkVDBCibf23ZyeVxB_8UYnDlhVularg",
    "authDomain": "porteiroeletronico-sel0373.firebaseapp.com",
    "databaseURL" : "gs://porteiroeletronico-sel0373.appspot.com/",
    "projectId": "porteiroeletronico-sel0373",
    "storageBucket": "porteiroeletronico-sel0373.appspot.com",
    "messagingSenderId": "209716118926",
    "appId": "1:209716118926:web:1311b757a0c27ed3c590df",
    "serviceAccount": "key.json"
  }

# Init firebase with your credentials
cred = credentials.Certificate("key.json")     #tem que baixar a chave e deixar na mesma pasta do arquivo ou então mudar o caminho
initialize_app(cred, {'storageBucket': 'porteiroeletronico-sel0373.appspot.com'})   #inicializa no nosso banco de dados
db = firestore.client()

#talvez dê conflitos
firebase = pyrebase.initialize_app(config)
bucket = storage.bucket()
storage2 = firebase.storage() #ta dando conflito quando usa esse storage (vai ter que mudar o nome, e ver em quais funções ta usando essa)
#se der erro eu troquei storage pra storage2


def captura_imagem(token, name): #funcional #capturar a imagem
    vid = cv2.VideoCapture(0)     
    time.sleep(0.5)
    _, imagem = vid.read()
    vid.release()
    print("ok")
    
    if token == 1:               #se token = 1 -> cadastro de usuário
        file_name = f"{name}.jpg"
        cv2.imwrite(file_name, imagem)
        return
    else:
        file_name = datetime.now().strftime("%Y%m%d_%H%M%S_")+"video.jpg"  #se tokem != ! -> ta enviando uma imagem do video
        imagem = cv2.resize(imagem, (0,0), fx=0.5, fy=0.5)
        cv2.imwrite(file_name, imagem)
        return file_name

def upload_and_get_url(fileName): #passa um arquivo e faz upload
    bucket = storage.bucket()
    blob = bucket.blob("cadastro/"+fileName) #cria o blob com o nome do arquivo
    blob.upload_from_filename(fileName) # faz o upload da imagem a partir do filename dela
    blob.make_public() #torna a imagem publica
    return blob.public_url #retorna a url

def cadastro(name): #função de cadastro
    image_name = f"{name}.jpg" #formata o nome da imagem que vai ser enviada pro storage
    captura_imagem(1, name) #tira a foto da imagem, com token = 1 e com o nome passado
    url = upload_and_get_url(image_name) #pega a url a partir da função feita pra isso
    os.remove(image_name) #remover a imagem que foi salva
    db.collection(u'cadastros').document(name).set({u'nome': name , u'foto': url}) #.add() é sem id
    return print("cadastro concluido com sucesso")

def remover(name): #remover do storage e do firestore, o nome da pessoa é passado e o arquivo é removido
    db.collection(u"cadastros").document(name).delete() #remove o elemento da coleção -> documento (nome dado)
    bucket = storage.bucket()
    blob = bucket.blob(name + ".jpg") #passa o nome da imagem pro bucket
    blob.delete() #remove o blob com o nome da imagem
    return print("cadastro e imagem removidas com sucesso")

def real_time_image(): #função para ficar capturando a imagem e ficar enviando para a coleção "video" que será mostrada no site   
    file_name = captura_imagem(2,"") #usa a função captura a imagem
    url = upload_and_get_url(file_name) #usa a função de guardar a imagem e obter a url
    os.remove(file_name) #remover a imagem que foi salva
    img_ref = db.collection(u'video').document(u'VE9Zu3Rn9RD5gDnckf2o')#.set({u'name': "video" , u'foto': url}) #joga a imagem na coleação
    img_ref.update({"foto": url})
    print("update realizado")
    return

def download_images(): #função para baixar as imagens do storage
    blobs = bucket.list_blobs(prefix = 'cadastro/')
    os.makedirs('cadastro')

# Faz o download de cada arquivo para a pasta de destino
    for blob in blobs:
        if not blob.name.endswith('/'):
            filename = blob.name
            print(filename)
            blob.download_to_filename(filename)
    #os.remove("images/video.jpg") #se der erro ta faltando voltar essa linha no caminho certo

#precis testar e avaliar as 2 funções a seguir ----------------
def known_face_encodings(directory):
    for filename in os.listdir(directory):        
        if filename not in encodings_names:
            encodings_names.append(filename)
            image_path = os.path.join(directory, filename)
            image = face_recognition.load_image_file(image_path)
            if len(face_recognition.face_encodings(image)) >0:
                encodings[filename.split('.')[0]] = face_recognition.face_encodings(image)[0]
    return encodings

def reconhecimento():
    name = captura_imagem(0, "user")
    image = face_recognition.load_image_file(name)
    face_locations = face_recognition.face_locations(image) 
    face_encodings = face_recognition.face_encodings(image, face_locations)
    
    encodings = known_face_encodings("cadastro/")

    # Comparar cada rosto encontrado com os rostos conhecidos
    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(list(encodings.values()), face_encoding)
    
        # Procurar entre as faces conhecidas para ver se alguma é uma correspondência
        if True in matches:
            matched_index = matches.index(True)
            name = list(encodings.keys())[matched_index]
            return name
    return "Desconhecido"

#doc_ref = db.collection('Token').document('token')

# Define a callback function to handle changes to the document
#def on_snapshot_callback(doc_snapshot, changes, read_time):
#    for doc in doc_snapshot:
#        if doc.exists:
#            doc_data = doc.to_dict()
#            token =doc_data.get('token')
#            nome = doc_data.get('nome')
#            # Compare the value of a specific field to a value in an if statement
#            if token == 1:
#                cadastro(nome)
#                print("ok cadastro")
#                db.collection(u'Token').document('token').set({u'name': "-" , u'token': 0})
#            if token == 2:
#                remover(nome)
#                print("ok remove")
#                db.collection(u'Token').document('token').set({u'name': "-" , u'token': 0})
            

#def start_firestore_watch():
#    doc_watch = doc_ref.on_snapshot(on_snapshot_callback)

# Start the Firestore watch in a separate thread
#firestore_watch_thread = threading.Thread(target=start_firestore_watch)
#firestore_watch_thread.start()
#download_images()

while True:
    t3 = time.time()
    print(reconhecimento())
    t4 = time.time()
    print(t4-t3)

#download_images()
#print(reconhecimento())

##########LINKS UTEIS##############
#https://firebase.google.com/s/results/?q=db%20collection
#https://firebase.google.com/docs/firestore/query-data/listen?hl=pt-br
#https://firebase.google.com/docs/firestore/manage-data/add-data?hl=pt-br

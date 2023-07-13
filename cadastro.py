import cv2  
import time
from firebase_admin import credentials, initialize_app, storage, firestore 
import os 
import pyrebase
import face_recognition
from datetime import datetime
import threading
import RPi.GPIO as GPIO
import time

print("inicializando porteiro")

#RASP CONFIGS
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
trig = 17
echo = 27
led_g = 10
led_r = 22
led_y = 9
button = 11
GPIO.setup(led_g,GPIO.OUT)
GPIO.setup(led_r,GPIO.OUT)
GPIO.setup(led_y, GPIO.OUT)
GPIO.setup(trig, GPIO.OUT)
GPIO.setup(echo, GPIO.IN)
GPIO.setup(button, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.output(led_g,GPIO.LOW)
GPIO.output(led_r,GPIO.LOW)
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
    liga_led(led_y)
    vid = cv2.VideoCapture(0)
    _, imagem = vid.read()
    vid.release()
    #print("Foto capturada")
    
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
    blob = bucket.blob("video/"+fileName) #cria o blob com o nome do arquivo
    blob.upload_from_filename(fileName) # faz o upload da imagem a partir do filename dela
    blob.make_public() #torna a imagem publica
    return blob.public_url #retorna a url

def cadastro(img_name, name): #função de cadastro
    url = upload_and_get_url(img_name) #pega a url a partir da função feita pra isso
    db.collection(u'video').document(f'{img_name}').set({u'nome': name , u'foto': url, u'date': datetime.now().strftime("%d/%m/%Y"), u'time': datetime.now().strftime("%H:%M:%S")})
    return 

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
    #print("update realizado")
    return

def download_images(): #função para baixar as imagens do storage
    blobs = bucket.list_blobs(prefix = 'cadastro/')
    os.makedirs('cadastro')

# Faz o download de cada arquivo para a pasta de destino
    for blob in blobs:
        if not blob.name.endswith('/'):
            filename = blob.name
            blob.download_to_filename(filename)

def known_face_encodings(directory):
    for filename in os.listdir(directory):        
        if filename not in encodings_names:
            encodings_names.append(filename)
            image_path = os.path.join(directory, filename)            
            image = face_recognition.load_image_file(image_path)
            if len(face_recognition.face_encodings(image)) >0:
                encodings[filename.split('.')[0]] = face_recognition.face_encodings(image)[0]
    return encodings

def reconhecimento(encodings):
    name = captura_imagem(0, "user")
    image = face_recognition.load_image_file(name)
    face_locations = face_recognition.face_locations(image) 
    face_encodings = face_recognition.face_encodings(image, face_locations)
    
    encodings = known_face_encodings("cadastro/")
    # Comparar cada rosto encontrado com os rostos conhecidos
    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(list(encodings.values()), face_encoding, tolerance = 0.6)
    
        # Procurar entre as faces conhecidas para ver se alguma é uma correspondência
        if True in matches:
            matched_index = matches.index(True)
            nome = list(encodings.keys())[matched_index]  
            return nome, True, name
    return "Desconhecido", False, name

def measure_distance(encodings):
    while True:
        distance= []
    
        GPIO.output(trig,True)
        time.sleep(0.00001)
        GPIO.output(trig,False)
    
        pulse_start = time.time()
        pulse_end = time.time()
    
        while GPIO.input(echo) == 0:
            pulse_start = time.time()
        while GPIO.input(echo) == 1:
            pulse_end = time.time()
    
        pulse_duration = pulse_end - pulse_start
        distance.append(round(pulse_duration*17150,2))
    
        if len(distance) > 5:
            distance.pop(0)

        mean_dist = sum(distance)/len(distance)
        if mean_dist < 10:
            x = 0
            matches = []
            names = []
            while x<2:
                name, match, img_name =reconhecimento(encodings)
                matches.append(match)
                names.append(name)
                x+=1
                print(name)
            return mean_dist, matches, img_name, names
        else:
            return mean_dist, [], "", []

def liga_led(led):
    GPIO.output(led,GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(led,GPIO.LOW)

def on_snapshot_callback(doc_snapshot, changes, read_time):
    for doc in doc_snapshot:
        if doc.exists:
            doc_data = doc.to_dict()
            token = int(doc_data.get('token'))
#            # Compare the value of a specific field to a value in an if statement
            if token == 1:
                os.system(f"rm -r /home/rasp/Porteiro_eletronico/cadastro") 
                download_images()
                db.collection(u'token_cadastro').document('token_cadastro').set({u'token': 0})
            
            elif token == 2:
                nome = db.collection('token_cadastro').document('nome_pessoa')
                nome = nome.get()
                filename = nome.to_dict()["filename"]  
                encodings_names.remove(filename)
                encodings.pop(filename)
                word=filename.split()
                filename ="\ ".join(word)
                os.system(f"rm -r /home/rasp/Porteiro_eletronico/cadastro/{filename}*")
                db.collection(u'token_cadastro').document('token_cadastro').set({u'token': 0})
                
def on_snapshot_callback2(doc_snapshot, changes, read_time):
    for doc in doc_snapshot:
        if doc.exists:
            doc_data = doc.to_dict()
            token = int(doc_data.get('token'))
#            # Compare1 the value of a specific field to a value in an if statement
            if token == 1:
                print("abrir porta")
                db.collection(u'token_abertura').document('token_abertura').set({u'token': 0})
                liga_led(led_g)
        
def b_callback(channel):
    print("Requisicao entrada")
    file_name = captura_imagem(2,"") #usa a função captura a imagem
    url = upload_and_get_url(file_name) #usa a função de guardar a imagem e obter a url
    db.collection(u'request').document(f'{file_name}').set({u'nome': file_name , u'foto': url, u'date': datetime.now().strftime("%d/%m/%Y"), u'time': datetime.now().strftime("%H:%M:%S"), u'view': "false"})

def start_firestore_watch():
    doc_watch = doc_ref.on_snapshot(on_snapshot_callback)
  
def start_firestore_watch2():
    doc_watch2 = doc_ref2.on_snapshot(on_snapshot_callback2)
    
doc_ref = db.collection('token_cadastro').document('token_cadastro')
doc_ref2 = db.collection('token_abertura').document('token_abertura')

# Start the Firestore watch in a separate thread
firestore_watch_thread = threading.Thread(target=start_firestore_watch)
firestore_watch_thread2 = threading.Thread(target=start_firestore_watch2)

firestore_watch_thread.start()
firestore_watch_thread2.start()
GPIO.add_event_detect(button, GPIO.FALLING, callback=b_callback, bouncetime=300)

try:
    contador_exclusão = 0
    encodings = known_face_encodings("cadastro/")
    print("Porteiro inicializado")
    while True:
        distance, matches, img_name, names = measure_distance(encodings)
        #print(f"A distância é: {distance}")
        for item in names:
            if item != "Desconhecido":
                name = item
        if True in matches:
            liga_led(led_g)
            cadastro(img_name,name)
        elif False in matches:
            liga_led(led_r)
       
        if contador_exclusão == 100:
            contador_exclusão = 0
            for file in os.listdir(os.curdir):
                if file.endswith(".jpg"):
                    os.system(f"rm /home/rasp/Porteiro_eletronico/{file}")
        contador_exclusão+=1
       
except KeyboardInterrupt:
    GPIO.cleanup()

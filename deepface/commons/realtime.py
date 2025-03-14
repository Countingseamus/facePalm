from email.mime.text import MIMEText
import os
from tqdm import tqdm
import numpy as np
import pandas as pd
import cv2
import time
import re
import smtplib, ssl

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from deepface import DeepFace
from deepface.extendedmodels import Age
from deepface.commons import functions, realtime, distance as dst
from deepface.detectors import FaceDetector
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from PIL import Image
import numpy as np
import pymsteams
import winsound

def beep_notification(occurences):
	duration = 1000  # millisecs
	freq = 440  # Hz
	for x in range(occurences):
		winsound.Beep(freq, duration)
def send_teams_notification(title, text):
	teamsChannel = pymsteams.connectorcard("link")
	teamsChannel.title(title)
	teamsChannel.text(text)
	teamsChannel.send()

def send_email(subject, contents, imagePath):
	port = 587  # For starttls
	smtp_server = "smtp.outlook.com"
	sender_email = "seamus.halton@bd.com"
	receiver_email = "seamus.halton@bd.com"
	password = os.environ.get('EMAIL_PASSWD')  # Environment variable set to store password
	message = MIMEMultipart()
	message['Subject'] = subject
	text = contents

	body = MIMEText(text, "plain")
	message.attach(body)

	with open(imagePath, 'rb') as f:
		img_data = f.read()
	image = MIMEImage(img_data, name=os.path.basename(imagePath))
	message.attach(image)

	context = ssl.create_default_context()
	with smtplib.SMTP(smtp_server, port) as server:
		server.ehlo()
		server.starttls(context=context)
		server.ehlo()
		server.login(sender_email, password)
		server.sendmail(sender_email, receiver_email, message.as_string())
		server.quit()

def analysis(db_path, model_name = 'VGG-Face', detector_backend = 'opencv', distance_metric = 'cosine', enable_face_analysis = True, source = 0, time_threshold = 5, frame_threshold = 5):

	#------------------------

	face_detector = FaceDetector.build_model(detector_backend)
	print("Detector backend is ", detector_backend)

	#------------------------

	input_shape = (224, 224); input_shape_x = input_shape[0]; input_shape_y = input_shape[1]

	text_color = (255,255,255)

	employees = []
	#check passed db folder exists
	if os.path.isdir(db_path) == True:
		for r, d, f in os.walk(db_path): # r=root, d=directories, f = files
			for file in f:
				if ('.jpg' in file):
					#exact_path = os.path.join(r, file)
					exact_path = r + "/" + file
					#print(exact_path)
					employees.append(exact_path)

	if len(employees) == 0:
		print("WARNING: There is no image in this path ( ", db_path,") . Face recognition will not be performed.")

	#------------------------

	if len(employees) > 0:

		model = DeepFace.build_model(model_name)
		print(model_name," is built")

		#------------------------

		input_shape = functions.find_input_shape(model)
		input_shape_x = input_shape[0]; input_shape_y = input_shape[1]

		#tuned thresholds for model and metric pair
		threshold = dst.findThreshold(model_name, distance_metric)

	#------------------------
	#facial attribute analysis models

	if enable_face_analysis == True:

		tic = time.time()

		emotion_model = DeepFace.build_model('Emotion')
		print("Emotion model loaded")

		age_model = DeepFace.build_model('Age')
		print("Age model loaded")

		gender_model = DeepFace.build_model('Gender')
		print("Gender model loaded")

		toc = time.time()

		print("Facial attibute analysis models loaded in ",toc-tic," seconds")

	#------------------------

	#find embeddings for employee list

	tic = time.time()

	#-----------------------

	pbar = tqdm(range(0, len(employees)), desc='Finding embeddings')

	#TODO: why don't you store those embeddings in a pickle file similar to find function?

	embeddings = []
	#for employee in employees:
	for index in pbar:
		employee = employees[index]
		pbar.set_description("Finding embedding for %s" % (employee.split("/")[-1]))
		embedding = []

		#preprocess_face returns single face. this is expected for source images in db.
		img = functions.preprocess_face(img = employee, target_size = (input_shape_y, input_shape_x), enforce_detection = False, detector_backend = detector_backend)
		img_representation = model.predict(img)[0,:]

		embedding.append(employee)
		embedding.append(img_representation)
		embeddings.append(embedding)

	df = pd.DataFrame(embeddings, columns = ['employee', 'embedding'])
	df['distance_metric'] = distance_metric

	toc = time.time()

	print("Embeddings found for given data set in ", toc-tic," seconds")

	#-----------------------

	pivot_img_size = 112 #face recognition result image

	#-----------------------

	freeze = False
	face_detected = False
	face_included_frames = 0 #freeze screen if face detected sequantially 5 frames
	freezed_frame = 0
	tic = time.time()

	cap = cv2.VideoCapture(source) #webcam

	labels = []
	unknownPersonIncrement = 1
	# We only want to send one alert for unidentified person for demo purposes
	sendAlert = True
	while(True):
		ret, img = cap.read()

		if img is None:
			break

		#cv2.namedWindow('img', cv2.WINDOW_FREERATIO)
		#cv2.setWindowProperty('img', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

		raw_img = img.copy()
		resolution = img.shape; resolution_x = img.shape[1]; resolution_y = img.shape[0]

		if freeze == False:

			try:
				#faces store list of detected_face and region pair
				faces = FaceDetector.detect_faces(face_detector, detector_backend, img, align = False)
			except: #to avoid exception if no face detected
				faces = []

			if len(faces) == 0:
				face_included_frames = 0
		else:
			faces = []

		detected_faces = []
		face_index = 0
		for face, (x, y, w, h) in faces:
			if w > 130: #discard small detected faces

				face_detected = True
				if face_index == 0:
					face_included_frames = face_included_frames + 1 #increase frame for a single face

				cv2.rectangle(img, (x,y), (x+w,y+h), (67,67,67), 1) #draw rectangle to main image

				cv2.putText(img, str(frame_threshold - face_included_frames), (int(x+w/4),int(y+h/1.5)), cv2.FONT_HERSHEY_SIMPLEX, 4, (255, 255, 255), 2)

				detected_face = img[int(y):int(y+h), int(x):int(x+w)] #crop detected face

				#-------------------------------------

				detected_faces.append((x,y,w,h))
				face_index = face_index + 1

				#-------------------------------------

		if face_detected == True and face_included_frames == frame_threshold and freeze == False:
			freeze = True
			print('Face detected')
			#base_img = img.copy()
			base_img = raw_img.copy()
			detected_faces_final = detected_faces.copy()
			tic = time.time()

		if freeze == True:

			toc = time.time()
			if (toc - tic) < time_threshold:

				if freezed_frame == 0:
					freeze_img = base_img.copy()
					#freeze_img = np.zeros(resolution, np.uint8) #here, np.uint8 handles showing white area issue

					for detected_face in detected_faces_final:
						x = detected_face[0]; y = detected_face[1]
						w = detected_face[2]; h = detected_face[3]

						cv2.rectangle(freeze_img, (x,y), (x+w,y+h), (67,67,67), 1) #draw rectangle to main image

						#-------------------------------

						#apply deep learning for custom_face

						custom_face = base_img[y:y+h, x:x+w]

						#-------------------------------
						#facial attribute analysis

						if enable_face_analysis == True:

							gray_img = functions.preprocess_face(img = custom_face, target_size = (48, 48), grayscale = True, enforce_detection = False, detector_backend = 'opencv')
							emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']
							emotion_predictions = emotion_model.predict(gray_img)[0,:]
							sum_of_predictions = emotion_predictions.sum()

							mood_items = []
							for i in range(0, len(emotion_labels)):
								mood_item = []
								emotion_label = emotion_labels[i]
								emotion_prediction = 100 * emotion_predictions[i] / sum_of_predictions
								mood_item.append(emotion_label)
								mood_item.append(emotion_prediction)
								mood_items.append(mood_item)

							emotion_df = pd.DataFrame(mood_items, columns = ["emotion", "score"])
							emotion_df = emotion_df.sort_values(by = ["score"], ascending=False).reset_index(drop=True)

							#background of mood box

							#transparency
							overlay = freeze_img.copy()
							opacity = 0.4

							if x+w+pivot_img_size < resolution_x:
								#right
								cv2.rectangle(freeze_img
									#, (x+w,y+20)
									, (x+w,y)
									, (x+w+pivot_img_size, y+h)
									, (64,64,64),cv2.FILLED)

								cv2.addWeighted(overlay, opacity, freeze_img, 1 - opacity, 0, freeze_img)

							elif x-pivot_img_size > 0:
								#left
								cv2.rectangle(freeze_img
									#, (x-pivot_img_size,y+20)
									, (x-pivot_img_size,y)
									, (x, y+h)
									, (64,64,64),cv2.FILLED)

								cv2.addWeighted(overlay, opacity, freeze_img, 1 - opacity, 0, freeze_img)

							for index, instance in emotion_df.iterrows():
								emotion_label = "%s " % (instance['emotion'])
								emotion_score = instance['score']/100

								bar_x = 35 #this is the size if an emotion is 100%
								bar_x = int(bar_x * emotion_score)

								if x+w+pivot_img_size < resolution_x:

									text_location_y = y + 20 + (index+1) * 20
									text_location_x = x+w

									if text_location_y < y + h:
										cv2.putText(freeze_img, emotion_label, (text_location_x, text_location_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

										cv2.rectangle(freeze_img
											, (x+w+70, y + 13 + (index+1) * 20)
											, (x+w+70+bar_x, y + 13 + (index+1) * 20 + 5)
											, (255,255,255), cv2.FILLED)

								elif x-pivot_img_size > 0:

									text_location_y = y + 20 + (index+1) * 20
									text_location_x = x-pivot_img_size

									if text_location_y <= y+h:
										cv2.putText(freeze_img, emotion_label, (text_location_x, text_location_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

										cv2.rectangle(freeze_img
											, (x-pivot_img_size+70, y + 13 + (index+1) * 20)
											, (x-pivot_img_size+70+bar_x, y + 13 + (index+1) * 20 + 5)
											, (255,255,255), cv2.FILLED)

							#-------------------------------

							face_224 = functions.preprocess_face(img = custom_face, target_size = (224, 224), grayscale = False, enforce_detection = False, detector_backend = 'opencv')

							age_predictions = age_model.predict(face_224)[0,:]
							apparent_age = Age.findApparentAge(age_predictions)

							#-------------------------------

							gender_prediction = gender_model.predict(face_224)[0,:]

							if np.argmax(gender_prediction) == 0:
								gender = "W"
							elif np.argmax(gender_prediction) == 1:
								gender = "M"

							#print(str(int(apparent_age))," years old ", dominant_emotion, " ", gender)

							analysis_report = str(int(apparent_age))+" "+gender

							#-------------------------------

							info_box_color = (46,200,255)

							#top
							if y - pivot_img_size + int(pivot_img_size/5) > 0:

								triangle_coordinates = np.array( [
									(x+int(w/2), y)
									, (x+int(w/2)-int(w/10), y-int(pivot_img_size/3))
									, (x+int(w/2)+int(w/10), y-int(pivot_img_size/3))
								] )

								cv2.drawContours(freeze_img, [triangle_coordinates], 0, info_box_color, -1)

								cv2.rectangle(freeze_img, (x+int(w/5), y-pivot_img_size+int(pivot_img_size/5)), (x+w-int(w/5), y-int(pivot_img_size/3)), info_box_color, cv2.FILLED)

								cv2.putText(freeze_img, analysis_report, (x+int(w/3.5), y - int(pivot_img_size/2.1)), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 111, 255), 2)

							#bottom
							elif y + h + pivot_img_size - int(pivot_img_size/5) < resolution_y:

								triangle_coordinates = np.array( [
									(x+int(w/2), y+h)
									, (x+int(w/2)-int(w/10), y+h+int(pivot_img_size/3))
									, (x+int(w/2)+int(w/10), y+h+int(pivot_img_size/3))
								] )

								cv2.drawContours(freeze_img, [triangle_coordinates], 0, info_box_color, -1)

								cv2.rectangle(freeze_img, (x+int(w/5), y + h + int(pivot_img_size/3)), (x+w-int(w/5), y+h+pivot_img_size-int(pivot_img_size/5)), info_box_color, cv2.FILLED)

								cv2.putText(freeze_img, analysis_report, (x+int(w/3.5), y + h + int(pivot_img_size/1.5)), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 111, 255), 2)

						#-------------------------------
						#face recognition

						custom_face = functions.preprocess_face(img = custom_face, target_size = (input_shape_y, input_shape_x), enforce_detection = False, detector_backend = 'opencv')

						#check preprocess_face function handled
						if custom_face.shape[1:3] == input_shape:
							if df.shape[0] > 0: #if there are images to verify, apply face recognition
								img1_representation = model.predict(custom_face)[0,:]
								#print(freezed_frame," - ",img1_representation[0:5])

								def findDistance(row):
									distance_metric = row['distance_metric']
									img2_representation = row['embedding']

									distance = 1000 #initialize very large value
									if distance_metric == 'cosine':
										distance = dst.findCosineDistance(img1_representation, img2_representation)
									elif distance_metric == 'euclidean':
										distance = dst.findEuclideanDistance(img1_representation, img2_representation)
									elif distance_metric == 'euclidean_l2':
										distance = dst.findEuclideanDistance(dst.l2_normalize(img1_representation), dst.l2_normalize(img2_representation))

									return distance

								df['distance'] = df.apply(findDistance, axis = 1)
								df = df.sort_values(by = ["distance"])

								candidate = df.iloc[0]
								employee_name = candidate['employee']
								best_distance = candidate['distance']

								#print(candidate[['employee', 'distance']].values)

								#if True:
								if best_distance <= threshold:
									# Detected in database
									display_img = cv2.imread(employee_name)
									display_img = cv2.resize(display_img, (pivot_img_size, pivot_img_size))

									label = employee_name.split("/")[-1].replace(".jpg", "")
									label = re.sub('[0-9]', '', label)

									print(f'Recognized {label}')
									text = f"""\
									Go welcome {label}."""

									# Send Greeting if name has not yet been sent i.e. only send greeting once
									sendGreeting = label not in labels
									if (sendGreeting):
										beep_notification(1)
										print(f'Sending greeting for {label}...')
										w, h = 512, 512
										imageOfKnownPerson = Image.fromarray(raw_img, 'RGB')
										imageOfKnownPerson.save(f'KnownPeople/{label}.jpg')
										send_email(f'{label} has entered the office', text, f'KnownPeople/{label}.jpg')
										send_teams_notification(f'{label} has entered the office', text)
										print('Greeting sent')
										labels.append(label)
									try:
										if y - pivot_img_size > 0 and x + w + pivot_img_size < resolution_x:
											#top right
											freeze_img[y - pivot_img_size:y, x+w:x+w+pivot_img_size] = display_img

											overlay = freeze_img.copy(); opacity = 0.4
											cv2.rectangle(freeze_img,(x+w,y),(x+w+pivot_img_size, y+20),(46,200,255),cv2.FILLED)
											cv2.addWeighted(overlay, opacity, freeze_img, 1 - opacity, 0, freeze_img)

											cv2.putText(freeze_img, label, (x+w, y+10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)

											#connect face and text
											cv2.line(freeze_img,(x+int(w/2), y), (x+3*int(w/4), y-int(pivot_img_size/2)),(67,67,67),1)
											cv2.line(freeze_img, (x+3*int(w/4), y-int(pivot_img_size/2)), (x+w, y - int(pivot_img_size/2)), (67,67,67),1)

										elif y + h + pivot_img_size < resolution_y and x - pivot_img_size > 0:
											#bottom left
											freeze_img[y+h:y+h+pivot_img_size, x-pivot_img_size:x] = display_img

											overlay = freeze_img.copy(); opacity = 0.4
											cv2.rectangle(freeze_img,(x-pivot_img_size,y+h-20),(x, y+h),(46,200,255),cv2.FILLED)
											cv2.addWeighted(overlay, opacity, freeze_img, 1 - opacity, 0, freeze_img)

											cv2.putText(freeze_img, label, (x - pivot_img_size, y+h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)

											#connect face and text
											cv2.line(freeze_img,(x+int(w/2), y+h), (x+int(w/2)-int(w/4), y+h+int(pivot_img_size/2)),(67,67,67),1)
											cv2.line(freeze_img, (x+int(w/2)-int(w/4), y+h+int(pivot_img_size/2)), (x, y+h+int(pivot_img_size/2)), (67,67,67),1)

										elif y - pivot_img_size > 0 and x - pivot_img_size > 0:
											#top left
											freeze_img[y-pivot_img_size:y, x-pivot_img_size:x] = display_img

											overlay = freeze_img.copy(); opacity = 0.4
											cv2.rectangle(freeze_img,(x- pivot_img_size,y),(x, y+20),(46,200,255),cv2.FILLED)
											cv2.addWeighted(overlay, opacity, freeze_img, 1 - opacity, 0, freeze_img)

											cv2.putText(freeze_img, label, (x - pivot_img_size, y+10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)

											#connect face and text
											cv2.line(freeze_img,(x+int(w/2), y), (x+int(w/2)-int(w/4), y-int(pivot_img_size/2)),(67,67,67),1)
											cv2.line(freeze_img, (x+int(w/2)-int(w/4), y-int(pivot_img_size/2)), (x, y - int(pivot_img_size/2)), (67,67,67),1)

										elif x+w+pivot_img_size < resolution_x and y + h + pivot_img_size < resolution_y:
											#bottom righ
											freeze_img[y+h:y+h+pivot_img_size, x+w:x+w+pivot_img_size] = display_img

											overlay = freeze_img.copy(); opacity = 0.4
											cv2.rectangle(freeze_img,(x+w,y+h-20),(x+w+pivot_img_size, y+h),(46,200,255),cv2.FILLED)
											cv2.addWeighted(overlay, opacity, freeze_img, 1 - opacity, 0, freeze_img)

											cv2.putText(freeze_img, label, (x+w, y+h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)

											#connect face and text
											cv2.line(freeze_img,(x+int(w/2), y+h), (x+int(w/2)+int(w/4), y+h+int(pivot_img_size/2)),(67,67,67),1)
											cv2.line(freeze_img, (x+int(w/2)+int(w/4), y+h+int(pivot_img_size/2)), (x+w, y+h+int(pivot_img_size/2)), (67,67,67),1)
									except Exception as err:
										print(str(err))
								else:
									# Not Detected in Database
									print('Face not Detected in Database')
									text = f"""\
									Please report this to security on site."""


									# Send Alert
									if (sendAlert):
										beep_notification(3)
										print('Sending Alert...')
										w, h = 512, 512
										imageOfUnknownPerson = Image.fromarray(raw_img, 'RGB')
										imageOfUnknownPerson.save(f'UnknownPeople/UnknownPerson{unknownPersonIncrement}.jpg')
										unknownPersonIncrement+1
										send_email('Unrecognized person alert!', text, f'UnknownPeople/UnknownPerson{unknownPersonIncrement}.jpg')
										send_teams_notification('Unrecognized person alert!', text)
										print('Alert sent.')
										# only send alert once for demo purposes
										sendAlert = False

						tic = time.time() #in this way, freezed image can show 5 seconds

						#-------------------------------

				time_left = int(time_threshold - (toc - tic) + 1)

				cv2.rectangle(freeze_img, (10, 10), (90, 50), (67,67,67), -10)
				cv2.putText(freeze_img, str(time_left), (40, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)

				cv2.imshow('img', freeze_img)

				freezed_frame = freezed_frame + 1
			else:
				face_detected = False
				face_included_frames = 0
				freeze = False
				freezed_frame = 0

		else:
			cv2.imshow('img',img)

		if cv2.waitKey(1) & 0xFF == ord('q'): #press q to quit
			break

	#kill open cv things
	cap.release()
	cv2.destroyAllWindows()

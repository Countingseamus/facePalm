from deepface import DeepFace

def compare_images(image1, image2):
    return DeepFace.verify(img1_path=image1, img2_path=image2)

def real_time_analysis():
    return DeepFace.stream(db_path='database', model_name='VGG-Face', detector_backend='opencv', distance_metric='cosine', enable_face_analysis=True, source=0, time_threshold=5, frame_threshold=5)

# Run the program
if __name__ == '__main__':
    real_time_analysis()
    # result1 = compare_images("MyPhoto.jpg", "Kevin_Bacon.jpg")
    # print(result1)
    # result2 = compare_images("MyPhoto.jpg", "Driving L And Me.jpg")
    # print(result2)
    # result3 = DeepFace.analyze("MyPhoto.jpg", ['age', 'gender', 'race', 'emotion'])
    # print(result3)
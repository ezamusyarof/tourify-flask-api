from flask import Flask, jsonify, request
from datetime import datetime
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np
import pandas as pd
import seaborn as sns
import pymysql.cursors
import hashlib
import random
import os
import json
import smtplib
sns.set_style('darkgrid')

app = Flask(__name__)

# Connection to database MySQL
db = pymysql.connect(
    host='[HOST]',
    user='[USERNAME]',
    password='[PASSWORD].',
    database='[DATABASE]',
    cursorclass=pymysql.cursors.DictCursor
)

# Run Query SQL
def query_database(query, params=()):
    try:
        with db.cursor() as cursor:
            cursor.execute(query, params)
            result = cursor.fetchall()
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        raise e

# User Registration
@app.route('/user/registration', methods=['POST'])
def registration_user():
    try:
        data = request.get_json()
        email = data['email']
        print(email)        
        query1 = 'SELECT * FROM data_pengguna WHERE email=%s'
        results1 = query_database(query1, (email,))
        
        if not results1:
            username = email.split('@')[0].replace('.', '-')
            query_id = "SELECT MAX(CAST(SUBSTRING(id, -3) AS UNSIGNED)) AS lastId FROM data_pengguna"
            results_id = query_database(query_id)
            random_num = random.randint(1, 9)
            current_year = str(datetime.now().year)[-2:]
            current_month = str(datetime.now().month).zfill(2)
            current_id = str(results_id[0]['lastId'] + 1).zfill(3)
            final_id = f'{random_num}{current_year}{current_month}1{current_id}'

            query2 = 'SELECT codeVerif FROM data_pengguna'
            results2 = query_database(query2)
            existing_codes = [row['codeVerif'] for row in results2]            
            code_verif = None
            while not code_verif or code_verif in existing_codes:
                code_verif = str(random.randint(100000, 999999)).zfill(6)

            # Send code verification via email
            sender_email = "[SENDER]"
            receiver_email = "[RECEIVER]"
            subject = "Tourify Account Verification Code - Action Required"
            message = f"Dear {username},\n\nYour account's security matters to us. Please use the following verification code to complete the registration account process:\n\nVerification Code: {code_verif}\n\nKeep this code confidential. It's time-sensitive and ensures secure access to your account. If you didn't request this, please contact us.\n\nBest Regards,\nTourify App"
            text = f"Subject: {subject}\n\n{message}"

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, "[PASSWORD]")
            server.sendmail(sender_email, receiver_email, text)
            
            query3 = 'INSERT INTO data_pengguna (id, email, username, codeVerif) VALUES (%s, %s, %s, %s)'
            query_database(query3, (final_id, email, username, code_verif))            
            query4 = 'UPDATE data_pengguna SET registrationDate = CURRENT_TIMESTAMP WHERE email=%s'
            query_database(query4, (email,))
            
            return jsonify({
                'statusCode': 200,
                'message': 'User registration successfully'
            }), 200
        else:
            return jsonify({
                'statusCode': 400,
                'error': 'User registration failed',
                'message': 'Email already exists'
            }), 400
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500

# Account Verification
@app.route('/user/verification', methods=['POST'])
def verification_user():
    try:
        data = request.get_json()
        email = data['email']
        codeVerif = data['codeVerif']
        print(email)
        query1 = 'SELECT * FROM data_pengguna WHERE email=%s AND codeVerif=%s'
        results1 = query_database(query1, (email, codeVerif))        
        if results1:
            query2 = 'UPDATE data_pengguna SET verificationDate = CURRENT_TIMESTAMP WHERE email=%s'
            query_database(query2, (email,))            
            return jsonify({
                'statusCode': 200,
                'message': 'User verification successfully'
            }), 200
        else:
            return jsonify({
                'statusCode': 400,
                'error': 'User verification failed',
                'message': 'Incorrect verification code'
            }), 400
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500

# Update User Password
@app.route('/user/password/<email>', methods=['PUT'])
def update_user_password(email):
    try:
        data = request.get_json()
        password = data['password']
        password_secured = hashlib.md5(password.encode()).hexdigest()        
        query1 = 'UPDATE data_pengguna SET password = %s WHERE email = %s'
        query_database(query1, (password_secured, email))        
        query2 = 'SELECT id FROM data_pengguna WHERE email = %s'
        results2 = query_database(query2, (email,))        
        return jsonify({
            'statusCode': 200,
            'message': 'Update password successfully',
            'data': {
                'userId': results2[0]['id'],
                'email': email
            }
        }), 200
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500

# User Login
@app.route('/user/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        email = data['email']
        password = data['password']
        password_secured = hashlib.md5(password.encode()).hexdigest()
        query1 = 'SELECT * FROM data_pengguna WHERE email=%s AND password=%s'
        results1 = query_database(query1, (email, password_secured))        
        if results1:
            query2 = 'UPDATE data_pengguna SET lastLoginDate = CURRENT_TIMESTAMP WHERE email=%s'
            query_database(query2, (email,))            
            query3 = 'SELECT id FROM data_pengguna WHERE email=%s'
            results3 = query_database(query3, (email,))
            return jsonify({
                'statusCode': 200,
                'message': 'Login successfully',
                'data': {
                    'userId': results3[0]['id'],
                    'email': email
                }
            }), 200
        else:
            return jsonify({
                'statusCode': 400,
                'error': 'Login failed',
                'message': 'Incorrect password'
            }), 400
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500

# User Logout
@app.route('/user/logout', methods=['POST'])
def logout_user():
    try:
        data = request.get_json()
        email = data['email']
        query = 'UPDATE data_pengguna SET lastLogoutDate = CURRENT_TIMESTAMP WHERE email=%s'
        results = query_database(query, (email,))
        print(results)
        return jsonify({
            'statusCode': 200,
            'message': 'Logout successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500

# Update User Data by Email
@app.route('/user/<email>', methods=['PUT'])
def update_user_data(email):
    try:
        data = request.get_json()
        gender = data['gender']
        birth_date = data['birth_date']
        photo = data['photo']
        telephone = data['telephone']
        whatsapp = data['whatsapp']
        lon = data['lon']
        lat = data['lat']
        query = 'UPDATE data_pengguna SET gender = %s, birth_date = %s, photo = %s, telephone = %s, whatsapp = %s, lon = %s, lat = %s WHERE email = %s'
        query_database(query, (gender, birth_date, photo, telephone, whatsapp, lon, lat, email))
        return jsonify({
            'statusCode': 200,
            'message': 'Update data successfully',
            'data': {'email': email}
        }), 200
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500

# Get All Destination Data
@app.route('/destinations', methods=['GET'])
def get_destinations():
    try:
        query = 'SELECT * FROM data_wisata'
        results = query_database(query)        
        new_results = []
        for destination in results:
            tour_guide_ids = json.loads(destination['tourGuide'])
            new_tour_guide_list = []            
            for guide_id in tour_guide_ids:
                query = 'SELECT * FROM data_pengguna WHERE id = %s'
                user_data = query_database(query, (guide_id))
                query = 'SELECT * FROM data_pemandu_wisata WHERE userId = %s'
                guide_data = query_database(query, (guide_id))
                print(user_data)
                print(guide_data)
                print(guide_id)
                if guide_data:
                    new_tour_guide_list.append({
                        "id": user_data[0]['id'],
                        "name": user_data[0]['name'],
                        "email": user_data[0]['email'],
                        "servicePrice": guide_data[0]['servicesFee'],
                        "photoProfile": user_data[0]['photo'],
                        "rating": guide_data[0]['rating'],
                        "totalReview": guide_data[0]['totalTrip']
                    })
            destination['tourGuide'] = new_tour_guide_list
            new_results.append(destination)
        return jsonify({
            'statusCode': 200,
            'message': 'Success',
            'data': new_results
        }), 200
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500

# Get Favorites Destination by Id
@app.route('/favorites/<userId>', methods=['GET'])
def get_favorite_destinations(userId):
    try:
        query = 'SELECT destinationId FROM data_wisata_favorit WHERE userId = %s'
        results = query_database(query, (userId,))
        data = [item['destinationId'] for item in results]        
        return jsonify({
            'statusCode': 200,
            'message': 'Success',
            'data': data
        }), 200
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500

# Add New Favorite Destination
@app.route('/favorites', methods=['POST'])
def add_favorite_destination():
    try:
        data = request.get_json()
        userId = data['userId']
        destinationId = data['destinationId']
        query1 = 'SELECT * FROM data_wisata_favorit WHERE userId=%s AND destinationId=%s'
        results1 = query_database(query1, (userId, destinationId))        
        if not results1:
            query2 = 'INSERT INTO data_wisata_favorit (destinationId, userId) VALUES (%s, %s)'
            query_database(query2, (destinationId, userId))            
            return jsonify({
                'statusCode': 200,
                'message': 'Added destination to favorites successfully'
            }), 200
        else:
            return jsonify({
                'statusCode': 400,
                'error': 'Add to favorites failed',
                'message': 'Destination already in favorites'
            }), 400
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500
    
# Remove a Favorite Destination
@app.route('/favorites', methods=['DELETE'])
def remove_favorite_destination():
    try:
        data = request.get_json()
        user_id = data['userId']
        destination_id = data['destinationId']
        query = 'DELETE FROM data_wisata_favorit WHERE userId=%s AND destinationId=%s'
        query_database(query, (user_id, destination_id))        
        return jsonify({
            'statusCode': 200,
            'message': 'Removed destination from favorites successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500

# Get All Culinary Data
@app.route('/culinary', methods=['GET'])
def get_culinary():
    try:
        query = 'SELECT * FROM data_kuliner'
        results = query_database(query)        
        return jsonify({
            'statusCode': 200,
            'message': 'Success',
            'data': results
        }), 200
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500

# Booking New Trip
@app.route('/booking', methods=['POST'])
def booking_new_trip():
    try:
        data = request.get_json()
        user_id = data['userId']
        destination_id = data['destinationId']
        tour_guide_id = data['tourGuideId']
        name = data['name']
        email = data['email']
        telephone = data['telephone']
        trip_date = data['tripDate']
        note = data['note']
        if not all([user_id, destination_id, name, email, telephone, trip_date]):
            return jsonify({
                'statusCode': 400,
                'message': 'Trip booked failed',
                'data': None
            }), 200        
        now = datetime.now()
        booking_code = f'TRF{now.strftime("%y%m%d%H%M%S")}{user_id}'
        
        # Get total price
        query_ticket_price = 'SELECT ticketPrice FROM data_wisata WHERE id = %s'
        results_ticket_price = query_database(query_ticket_price, [destination_id])
        total_payment = results_ticket_price[0]['ticketPrice']
        if tour_guide_id != 0:
            query_service_fee = 'SELECT servicesFee FROM data_pemandu_wisata WHERE userId = %s'
            results_service_fee = query_database(query_service_fee, [tour_guide_id])
            total_payment = total_payment + results_service_fee[0]['servicesFee']
        
        query_insert_booking = 'INSERT INTO data_booking (userId, destinationId, tourGuideId, bookingCode, tripDate, totalPayment, ordererNote, statusPayment, bookingDate) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)'
        query_database(query_insert_booking, [user_id, destination_id, tour_guide_id, booking_code, trip_date, total_payment, note, 1])
        query_insert_booking = 'UPDATE data_pengguna SET name=%s, whatsapp=%s WHERE id=%s'
        query_database(query_insert_booking, [name, telephone, user_id])
        query_insert_booking = 'UPDATE data_pemandu_wisata SET totalTrip = totalTrip + 1 WHERE userId = %s;'
        query_database(query_insert_booking, [tour_guide_id])
        query_select_booking = 'SELECT * FROM data_booking WHERE bookingCode = %s'
        results_booking = query_database(query_select_booking, [booking_code])
        
        with_tour_guide = True if tour_guide_id != 0 else False
        return jsonify({
            'statusCode': 200,
            'message': 'Trip booked',
            'data': {
                'id': results_booking[0]['id'],
                'code': booking_code,
                'total': total_payment,
                'withTourGuide': with_tour_guide,
                'statusPayment': 1
            }
        }), 200
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500

# Scanning Object
@app.route('/scanning', methods=['POST'])
def scanning_object():
    UPLOAD_FOLDER = './'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    try:
        img = request.files["image"]
        print(img.filename)        
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
        img.save(img_path)
        
        model = load_model('objek.h5') # Load trained model
        img_path = './'+img.filename
        print(img_path)
        img = image.load_img(img_path, target_size=(224, 224))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array /= 255.0

        # Make prediction
        prediction = model.predict(img_array)
        predicted_class = np.argmax(prediction)
        class_labels = ['Monumen Nasional', 'Monumen Selamat Datang', 'Patung Sudirman', 'Rumah Boneka', 'Teater IMAX Keong Mas', 'Masjid Istiqlal', 'Museum Nasional']
        predicted_label = class_labels[predicted_class]

        # Load data from CSV
        csv_path = './objek.csv'
        df = pd.read_csv(csv_path)

        # Map class labels to captions from the CSV file
        class_captions = dict(zip(df['Object'], df['Caption']))
        class_photos = dict(zip(df['Object'], df['Photo']))

        # Display the prediction
        print("Predicted Class:", predicted_class)
        print("Predicted Label:", predicted_label)

        # Display the corresponding caption from the CSV file
        predicted_caption = class_captions.get(predicted_label, "Caption not found")
        predicted_photo = class_photos.get(predicted_label, "Photo not found")
        print("Predicted Caption:", predicted_caption)

        os.remove(img_path)
        return jsonify({
            'statusCode': 200,
            'message': 'Success',
            'data': {
                'name': predicted_label,
                'caption': predicted_caption,
                'photo': predicted_photo
            }
        }), 200
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500

@app.route('/mytickets/<userId>', methods=['GET'])
def get_user_tickets(userId):
    try:
        query = 'SELECT * FROM data_booking WHERE userId = %s'
        results = query_database(query, (userId,))
        guide_id = results[0]['tourGuideId']

        query = 'SELECT * FROM data_pengguna WHERE id = %s'
        user_data = query_database(query, (guide_id))
        query = 'SELECT * FROM data_pemandu_wisata WHERE userId = %s'
        guide_data = query_database(query, (guide_id))
        
        if guide_data:
            results[0]['tourGuideData'] = ({
                "id": user_data[0]['id'],
                "name": user_data[0]['name'],
                "email": user_data[0]['email'],
                "servicePrice": guide_data[0]['servicesFee'],
                "photoProfile": user_data[0]['photo'],
                "rating": guide_data[0]['rating'],
                "totalTrip": guide_data[0]['totalTrip']
            })
        else:
            results[0]['tourGuideData'] = None

        return jsonify({
            'statusCode': 200,
            'message': 'Success',
            'data': results
        }), 200
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500

# Predict Recommendation Destinations
csv_path_destinations = './destinations.csv'
csv_path_ratings = './ratings.csv'
df_destinations = pd.read_csv(csv_path_destinations)
df_ratings = pd.read_csv(csv_path_ratings)
place_ids = df_ratings['id'].unique().tolist()
place_to_place_encoded = {x: i for i, x in enumerate(place_ids)}

def predict(user_place_array):
    return np.random.rand(len(user_place_array))

def get_random_recommendations():
    return np.random.choice(df_destinations['id'], size=10, replace=False)

@app.route('/predict', methods=['POST'])
def predict_route():
    try:
        data = request.get_json()
        user_id = data['user_id']
        print(user_id)
        if user_id in df_ratings['User_id'].values:
            place_rated = df_ratings[df_ratings.User_id == user_id]
            place_not_rated = df_destinations[~df_destinations['id'].isin(place_rated['id'].values)]['id'].tolist()
            user_place_array = np.hstack(
                ([[user_id]] * len(place_not_rated), [[place_to_place_encoded.get(x)] for x in place_not_rated])
            )        
            ratings = predict(user_place_array).flatten()
            top_ratings_indices = ratings.argsort()[-10:][::-1]
            recommended_place_ids = [place_not_rated[x] for x in top_ratings_indices]
            recommended_places = df_destinations[df_destinations['id'].isin(recommended_place_ids)]
            return jsonify({
                'statusCode': 200,
                'message': 'Success',
                'data': {
                    'user_id': user_id,
                    'recommendations': recommended_places.to_dict('records')
                }
            }), 200
        else:
            random_recommendations = get_random_recommendations()
            random_places = df_destinations[df_destinations['id'].isin(random_recommendations)]
            return jsonify({
                'statusCode': 200,
                'message': 'Success',
                'data': {
                    'user_id': user_id,
                    'recommendations': recommended_places.to_dict('records')
                }
            }), 200
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)

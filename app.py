import pickle
import streamlit as st
import requests
import sqlite3
import time
from dotenv import load_dotenv
import os

def configure():
    load_dotenv()
    
# Function to fetch movie poster
def fetch_poster(movie_id, max_retries=3, retry_delay=1):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US"
    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            #print("Movie id "+ movie_id+" Poster Fetch Successfull")
            poster_path = data['poster_path']
            full_path = "https://image.tmdb.org/t/p/w500/" + poster_path
            return full_path
        except (requests.exceptions.RequestException, KeyError) as err:
            print(f"Error fetching poster (Attempt {attempt + 1}): {err}")
            time.sleep(retry_delay)
    return None


# Function to recommend movies
def recommend(movie):
    index = movies[movies['title'] == movie].index[0]
    distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
    recommended_movie_names = []
    recommended_movie_posters = []
    for i in distances[1:6]:
        movie_id = movies.iloc[i[0]].movie_id
        poster = fetch_poster(movie_id)
        if poster:
            recommended_movie_posters.append(poster)
            recommended_movie_names.append(movies.iloc[i[0]].title)
    return recommended_movie_names, recommended_movie_posters


from twilio.rest import Client

def send_sms(phone_number, movie_name, time_slot, seats):
    configure()
    # Your Twilio credentials (replace these with your own)
    account_sid = os.getenv('account_sid')
    auth_token = os.getenv('auth_token')
    twilio_number = os.getenv('twilio_number')
    
    # Ticket details to be sent
    ticket_details = (
        f"🎥 Movie: {movie_name}\n"
        f"🕒 Time Slot: {time_slot}\n"
        f"💺 Seats: {', '.join(seats)}\n"
        "Enjoy your movie! 🍿"
    )
    
    # Create a Twilio client
    client = Client(account_sid, auth_token)
    
    try:
        # Send the SMS
        message = client.messages.create(
            body=ticket_details,
            from_=twilio_number,
            to=phone_number
        )
        print(f"Message sent: SID={message.sid}")
        return True
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return False
    
# Function to simulate sending SMS (Replace this with your SMS API)
# def send_sms(phone_number, movie_name, time_slot, seats):
#     try:
#         # Simulate SMS sending (Replace with SMS service like Twilio)
#         ticket_details = (
#             f"Movie: {movie_name}\n"
#             f"Time Slot: {time_slot}\n"
#             f"Seats: {', '.join(seats)}\n"
#             "Enjoy your movie!"
#         )
#         print(f"Message sent to {phone_number}:\n{ticket_details}")
#         return True
#     except Exception as e:
#         print(f"Failed to send SMS: {e}")
#         return False


# Database setup
conn = sqlite3.connect('seat_bookings.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS bookings
             (movie_name TEXT, time_slot TEXT, seat_number TEXT)''')
conn.commit()


# Streamlit app setup
st.header('🎥 Movie Recommender & Ticket Booking System')
movies = pickle.load(open('artifacts/movie_list.pkl', 'rb'))
similarity = pickle.load(open('artifacts/similarity.pkl', 'rb'))

# Initialize session state
if 'app_state' not in st.session_state:
    st.session_state.app_state = 'select_movie'
    st.session_state.selected_seats = []


# App navigation logic
if st.session_state.app_state == 'select_movie':
    # Movie selection
    movie_list = movies['title'].values
    selected_movie = st.selectbox("Type or select a movie from the dropdown", movie_list)

    if st.button('Show Recommendations'):
        recommended_movie_names, recommended_movie_posters = recommend(selected_movie)
        st.session_state.recommended_movie_names = recommended_movie_names
        st.session_state.recommended_movie_posters = recommended_movie_posters
        st.session_state.app_state = 'show_recommendations'

elif st.session_state.app_state == 'show_recommendations':
    # Display recommendations
    col_list = st.columns(5)
    for i, (name, poster) in enumerate(zip(st.session_state.recommended_movie_names, st.session_state.recommended_movie_posters)):
        with col_list[i]:
            st.text(name)
            st.image(poster)
            if st.button("Book", key=f"book_{i}"):
                st.session_state.app_state = 'book_ticket'
                st.session_state.selected_movie_name = name

elif st.session_state.app_state == 'book_ticket':
    # Booking details
    st.subheader(f"🎟️ Book Tickets for {st.session_state.selected_movie_name}")
    show_time_slots = ["10:00 AM", "1:00 PM", "4:00 PM", "7:00 PM", "10:00 PM"]
    selected_time_slot = st.selectbox("Select a Time Slot", show_time_slots)

    # Retrieve already booked seats
    c.execute("SELECT seat_number FROM bookings WHERE movie_name=? AND time_slot=?", 
              (st.session_state.selected_movie_name, selected_time_slot))
    booked_seats = [row[0] for row in c.fetchall()]

    # Seat layout
    seat_layout = [
        ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', 'S10'],
        ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'M10'],
        ['U1', 'U2', 'U3', 'U4', 'U5', 'U6', 'U7', 'U8', 'U9', 'U10']
    ]

    st.subheader("Select Your Seats")
    for row_idx, row in enumerate(seat_layout):
        cols = st.columns(len(row))
        for col_idx, seat in enumerate(row):
            with cols[col_idx]:
                if seat in booked_seats:
                    st.button(seat, disabled=True, key=f"seat_{seat}")
                else:
                    if st.button(seat, key=f"seat_{seat}"):
                        if seat not in st.session_state.selected_seats:
                            st.session_state.selected_seats.append(seat)
                            st.success(f"{seat} selected!")
                        else:
                            st.session_state.selected_seats.remove(seat)
                            st.warning(f"{seat} deselected!")

    # Phone number input
    st.subheader("Enter Your Details")
    phone_number = st.text_input("Enter your phone number", key="phone_number", max_chars=15, placeholder="+1234567890")

    # Proceed with booking
    if st.button("Proceed to Payment"):
        if not phone_number:
            st.error("Please enter your phone number!")
        elif st.session_state.selected_seats:
            # Update database with the new booking
            for seat in st.session_state.selected_seats:
                c.execute("INSERT INTO bookings VALUES (?, ?, ?)", 
                          (st.session_state.selected_movie_name, selected_time_slot, seat))
            conn.commit()

            # Send ticket details via SMS
            if send_sms(phone_number, st.session_state.selected_movie_name, selected_time_slot, st.session_state.selected_seats):
                st.success(f"Booking confirmed! Ticket details sent to {phone_number}")
                st.session_state.selected_seats = []
            else:
                st.error("Failed to send ticket details. Please try again.")
        else:
            st.error("Please select at least one seat!")




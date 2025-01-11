import streamlit_authenticator as stauth

# List of plaintext passwords
passwords = ['password1', 'password2', 'password3']

# Generate hashed passwords
hashed_passwords = stauth.Hasher(passwords).generate()

print(hashed_passwords)
# # A9lX4y

# import random
# import string

# def generate_otp():
#     otp = ''
#     for _ in range(2):  # Two repetitions for 6 chars
#         upper = random.choice(string.ascii_uppercase)
#         digit = random.choice('0123456789')
#         lower = random.choice(string.ascii_lowercase)
#         otp += upper + digit + lower
#     return otp

# # Usage
# otp = generate_otp()
# print(f"Your OTP: {otp}")


import random as r   # MISSING IMPORT

def genotp():
    otp = ""
    up = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
    lo = [chr(i) for i in range(ord('a'), ord('z') + 1)]
    for i in range(2):
        otp += r.choice(up) + str(r.randint(0, 9)) + r.choice(lo)
    return otp

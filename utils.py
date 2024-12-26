from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
from PIL import Image
import io

# Password context used to hash and verify the password to ensure security.
pwd_context = CryptContext(schemes=['bcrypt'], deprecated = 'auto')
serializer = URLSafeTimedSerializer('secret', salt='password_reset')



def get_hash_password(raw_password: str) -> str :
    
    return pwd_context.hash(raw_password) 

def verify_password(raw_password: str, hash_password: str) -> bool :

    return pwd_context.verify(raw_password, hash_password)


def get_processed_data(data: dict) -> dict:   
    processed_data = data.copy()
    for key, value in processed_data.items():
            if type(value) == str:
                processed_data[key] = value.strip().title()
    return processed_data



def get_compressed_image(
    image: bytes, size: tuple[int, int] = (200, 200),
    quality: int = 75
) -> bytes:

    img_file = io.BytesIO(image) # Makes the binary data as a file-like object, so PIL can read. 
    with Image.open(img_file) as img:
        # Convert the image into RGB format to ensure compatability.
        img.convert('RGB')
        # Resize the image.
        img.thumbnail(size, resample = Image.Resampling.LANCZOS)

        # Create a file-like object to write compressed image.
        compressed_stream = io.BytesIO()
        img.save(compressed_stream, format = 'JPEG', quality = quality)

        # After write the data, need to move the cursor point to initial place, So that it reads from the beginning.
        compressed_stream.seek(0)

        # Convert the file like object into binary.
        compressed_binary_data: bytes = compressed_stream.read()

        return compressed_binary_data



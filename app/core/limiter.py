from slowapi import Limiter
from slowapi.util import get_remote_address

# Создаем единый инстанс лимитера
limiter = Limiter(key_func=get_remote_address)

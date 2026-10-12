import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

# Em produção usa DATABASE_URL diretamente, em dev constrói a partir das variáveis
DATABASE_URL = os.getenv('DATABASE_URL') or \
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

_opcoes = {'pool_pre_ping': True, 'hide_parameters': True}
if DATABASE_URL.startswith('postgresql'):
    _opcoes.update(pool_timeout=5, connect_args={'connect_timeout': 5})
engine = create_engine(DATABASE_URL, **_opcoes)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

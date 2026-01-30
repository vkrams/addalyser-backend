from app.core.db import engine
from app.core.db import Base
from app.db import models  # IMPORTANT: ensure models are imported

def main():
    Base.metadata.create_all(bind=engine)
    print("TABLES CREATED")

if __name__ == "__main__":
    main()

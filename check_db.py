from database import session_scope
from models import Communication, Person
from sqlalchemy import func
from app import app

def check_database():
    with app.app_context():
        with session_scope() as session:
            # Check communications
            comms = session.query(Communication).all()
            print(f'Found {len(comms)} communications total')
            
            comms_with_person = session.query(Communication).filter(Communication.person_id != None).all()
            print(f'Found {len(comms_with_person)} communications with person_id set')
            
            # Check people with email addresses
            people = session.query(Person).filter(Person.email != None, Person.email != '').all()
            print(f'Found {len(people)} people with email addresses:')
            for person in people[:5]:
                print(f'  - {person.first_name} {person.last_name}: {person.email}')
            
            # Check if any communications match people by email
            if comms and people:
                print("\nChecking for email matches between communications and people:")
                for comm in comms[:5]:
                    print(f"Communication ID: {comm.id}, Type: {comm.type}, Subject: {comm.subject}")
                    if hasattr(comm, 'message_data') and comm.message_data:
                        sender = comm.message_data.get('from', 'Unknown')
                        recipient = comm.message_data.get('to', 'Unknown')
                        print(f"  From: {sender}, To: {recipient}")
                    else:
                        print("  No message data available")

if __name__ == "__main__":
    check_database() 
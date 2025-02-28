from models import session_scope, Person, Church

def check_db():
    with session_scope() as session:
        people_count = session.query(Person).count()
        churches_count = session.query(Church).count()
        
        print(f"People count: {people_count}")
        print(f"Churches count: {churches_count}")
        
        if people_count > 0:
            people = session.query(Person).all()
            print("\nPeople:")
            for person in people:
                print(f"  ID: {person.id}, Name: {person.get_name()}")
        
        if churches_count > 0:
            churches = session.query(Church).all()
            print("\nChurches:")
            for church in churches:
                print(f"  ID: {church.id}, Name: {church.get_name()}")

if __name__ == "__main__":
    check_db() 
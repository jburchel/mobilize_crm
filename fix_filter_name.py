"""
This script updates the filter_name logic in the communications_route and all_communications_route functions
to handle Row objects correctly.
"""

import re

def update_filter_name_logic(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern for communications_route filter_name logic
    comm_route_pattern = r'# Get the filter name if applicable\s+filter_name = None\s+if person_id:\s+person = session\.query\(Person\)\.filter\(Person\.id == person_id_int\)\.first\(\)\s+if person:\s+filter_name = person\.get_name\(\)'
    
    # Replacement for communications_route
    comm_route_replacement = """# Get the filter name if applicable
        filter_name = None
        if person_id:
            try:
                person_id_int = int(person_id)
                person = session.query(Person).filter(Person.id == person_id_int).first()
                if person:
                    # Use first_name and last_name directly instead of get_name()
                    filter_name = f"{person.first_name} {person.last_name}"
            except ValueError:
                current_app.logger.error(f"Invalid person_id: {person_id}")"""
    
    # Pattern for church filter_name in communications_route
    church_pattern = r'elif church_id:\s+church = session\.query\(Church\)\.filter\(Church\.id == church_id_int\)\.first\(\)\s+if church:\s+filter_name = church\.get_name\(\)'
    
    # Replacement for church filter_name
    church_replacement = """elif church_id:
            try:
                church_id_int = int(church_id)
                church = session.query(Church).filter(Church.id == church_id_int).first()
                if church:
                    # Use church_name directly instead of get_name()
                    filter_name = church.church_name
            except ValueError:
                current_app.logger.error(f"Invalid church_id: {church_id}")"""
    
    # Pattern for all_communications_route filter_name logic
    all_comm_pattern = r'# Get filter name if applicable\s+filter_name = None\s+if person_id:\s+try:\s+person_id_int = int\(person_id\)\s+person = session\.query\(Person\)\.filter_by\(id=person_id_int\)\.first\(\)\s+if person:\s+filter_name = person\.get_name\(\)'
    
    # Replacement for all_communications_route
    all_comm_replacement = """# Get filter name if applicable
        filter_name = None
        if person_id:
            try:
                person_id_int = int(person_id)
                person = session.query(Person).filter_by(id=person_id_int).first()
                if person:
                    # Use first_name and last_name directly instead of get_name()
                    filter_name = f"{person.first_name} {person.last_name}"
                    current_app.logger.debug(f"Found person: {filter_name}")
                else:
                    current_app.logger.warning(f"Person with ID {person_id_int} not found")
            except ValueError:
                current_app.logger.error(f"Invalid person_id: {person_id}")"""
    
    # Pattern for church filter_name in all_communications_route
    all_church_pattern = r'elif church_id:\s+try:\s+church_id_int = int\(church_id\)\s+church = session\.query\(Church\)\.filter_by\(id=church_id_int\)\.first\(\)\s+if church:\s+filter_name = church\.get_name\(\)'
    
    # Replacement for church filter_name in all_communications_route
    all_church_replacement = """elif church_id:
            try:
                church_id_int = int(church_id)
                church = session.query(Church).filter_by(id=church_id_int).first()
                if church:
                    # Use church_name directly instead of get_name()
                    filter_name = church.church_name
                    current_app.logger.debug(f"Found church: {filter_name}")
                else:
                    current_app.logger.warning(f"Church with ID {church_id_int} not found")
            except ValueError:
                current_app.logger.error(f"Invalid church_id: {church_id}")"""
    
    # Apply all replacements
    content = re.sub(comm_route_pattern, comm_route_replacement, content, flags=re.DOTALL)
    content = re.sub(church_pattern, church_replacement, content, flags=re.DOTALL)
    content = re.sub(all_comm_pattern, all_comm_replacement, content, flags=re.DOTALL)
    content = re.sub(all_church_pattern, all_church_replacement, content, flags=re.DOTALL)
    
    # Update the search_communications function to handle Row objects
    search_pattern = r'recipient_name = "N/A"\s+if comm\.person:\s+recipient_name = comm\.person\.get_name\(\)\s+elif comm\.church:\s+recipient_name = comm\.church\.get_name\(\)'
    
    search_replacement = """recipient_name = "N/A"
            if comm.person:
                if hasattr(comm.person, 'get_name'):
                    recipient_name = comm.person.get_name()
                else:
                    recipient_name = f"{comm.person.first_name} {comm.person.last_name}"
            elif comm.church:
                if hasattr(comm.church, 'get_name'):
                    recipient_name = comm.church.get_name()
                else:
                    recipient_name = comm.church.church_name"""
    
    content = re.sub(search_pattern, search_replacement, content, flags=re.DOTALL)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Updated filter_name logic in {file_path}")

if __name__ == "__main__":
    update_filter_name_logic("routes/communications.py") 
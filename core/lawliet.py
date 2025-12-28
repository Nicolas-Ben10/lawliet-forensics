import os
import sys
import tqdm
from signatures import SIGNATURES
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.progress import Progress

OVERLAP = 1024 #this is necessary because we need to search for the signature in the previous 1024 bytes
LIMIT_SECURITY = 400*1024*1024 #limiting the search to 400MB because i don't wanna to have a disaster
console = Console()


ASCII_ART = """
 [bold red]██╗      █████╗ ██╗    ██╗██╗     ██╗███████╗████████╗[/bold red]
 [bold white]██║     ██╔══██╗██║    ██║██║     ██║██╔════╝╚══██╔══╝[/bold white]
 [bold red]██║     ███████║██║ █╗ ██║██║     ██║█████╗     ██║   [/bold red]
 [bold white]██║     ██╔══██║██║███╗██║██║     ██║██╔══╝     ██║   [/bold white]
 [bold red]███████╗██║  ██║╚███╔███╔╝███████╗██║███████╗   ██║   [/bold red]
 [bold white]╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝╚═╝╚══════╝   ╚═╝   [/bold white]
           [italic cyan]Digital Forensics File Carver[/italic cyan]
           [italic blue]By Nicolas Pauferro[/italic blue]
           [italic purple]Supported files: jpg, png, pdf, gif, zip, mp4 and pptx[/italic purple]
           [italic white]txt, mp3, rar and docx cooming soon...[/italic white]

"""

def print_welcome():
    console.print(Panel(ASCII_ART, subtitle="Version - 1.0", border_style="blue"))

def carve_zip(i, outpath, header_pos, g): #this was the hardest function to write, so everything is commented
    original_pos = g.tell() #just saving the position that we had initially
    g.seek(header_pos) #move to the header position we have saved to header_pos variable
    max_search = 100 * 1024 * 1024 #limiting the search to 100MB because i don't wanna to have a disaster
    data_to_search = g.read(max_search)
    
    eocd_pos = data_to_search.rfind(b'\x50\x4b\x05\x06') # Finding the End Of central directory (it is some ZIP shit)
    
    if eocd_pos != -1:
        comment_len_offset = eocd_pos + 20 #the comment length is stored in the 20th byte of the End Of central directory
        if comment_len_offset + 2 <= len(data_to_search): #Checking if the comment is valid
            comment_len = int.from_bytes(data_to_search[comment_len_offset:comment_len_offset+2], 'little')
            total_zip_size = eocd_pos + 22 + comment_len
            g.seek(header_pos) #if all this shit is valid we move the pointer to header_pos and read the file
            zip_data = g.read(total_zip_size) #reading the file
            name = f"restored_{i}.zip" #the name of the file
            with open(os.path.join(outpath, "zip", name), 'wb') as rf: #opening the file in write binary mode
                rf.write(zip_data)  #writing the file
            g.seek(original_pos) #return the pointer to the original position for not fucking up the program
            return True #return true if the file was restored successfully

    g.seek(original_pos) #return to the original position even if everything's gone wrong
    return False #return false if the file was not restored successfully

def carve_mp4(i, outpath, header, g):
    g.seek(header) #go to the header position
    size_mp4 = 0 #initialize some variables
    found_moov = False
    found_ftyp = False
    
    try:
        while size_mp4 < LIMIT_SECURITY: #limiting the size for security reasons (my pc not crashing pls)
            current_box_pos = header + size_mp4
            g.seek(current_box_pos)
            
            headers = g.read(8) #read the first 8 bytes of the file
            if len(headers) < 8: #if this headers length is less than 8 , is broken
                break
            
            box_size = int.from_bytes(headers[:4], byteorder='big') #the box size is stored in the first 4 bytes
            box_name = headers[4:] #the box name is stored in the next 4 bytes

            if box_size < 8: 
                break #if the box size is less than 8, is broken
            
            if box_name == b"ftyp": 
                found_ftyp = True #this thing is important for the majority of mp4 files
            if box_name == b"moov": 
                found_moov = True #this also
            
            if box_size == 1: 
                box_size = int.from_bytes(g.read(8), byteorder='big') # some mp4 files do this shit and store the size in the next 8 bytes
            
            if size_mp4 + box_size > LIMIT_SECURITY: # again, security reasons...
                break
                
            size_mp4 = size_mp4 + box_size #incrementing size_mp4 file size
            
            if found_ftyp and found_moov:
                g.seek(header + size_mp4)
                check = g.read(4)
                if not check or int.from_bytes(check, 'big') == 0: #checking if there something to read or just zeros, in any case, the file has ended so we break the loop
                    break

        if size_mp4 > 8 and found_ftyp: #if the file is valid...
            g.seek(header) #move the pointer to the initial position of the file
            name = f"restored_{i}.mp4" #name of the file
            target_path = os.path.join(outpath, "mp4", name) #patjh of the file
            
            with open(target_path, 'wb') as restored_file: #opening the file in write binary mode
                remaining = size_mp4 #remaining size of the file (we are writing in chunks this time for not crashing the application)
                while remaining > 0:
                    chunk_to_read = min(1024 * 1024, remaining) #reading the file in chunks of 1MB or less if the file is smaller
                    chunk = g.read(chunk_to_read) #reading the file
                    if not chunk: break
                    restored_file.write(chunk) #writing the file
                    remaining -= len(chunk)
            
            
            return True
            
        return False
    except Exception as e:
        print(f"Error carving the mp4 file: {e}") #printing the error
        return False


def carve(isopath, outpath, buffer_size):
    for format in SIGNATURES:
        os.makedirs(os.path.join(outpath, format), exist_ok=True)

    with open(isopath, 'rb') as f:
        try:
            totalsize = os.path.getsize(isopath)
        except PermissionError:
            print("Error: You need to run as sudo to access the pendrive directly.")
            return
        except OSError as e:
            print(f"Error reading the device: {e}")
            return
        progress = tqdm.tqdm(total=totalsize, unit='B', unit_scale=True)
        flag = 0
        i = 0
        while flag==0: #yeah this is different but it works and i was used to C , not python :D
            actual_position = f.tell()
            data = f.read(buffer_size)
            if not data:
                print("Nothing more to read")
                flag=1
            for format in SIGNATURES: 
                # here i am just initializing some useful variables
                position_header = -1
                search_pointer = 0
                while True:
                    if format == "mp4":
                        target_signature = b'ftyp' #why does mp4 have a so fucking different signature?
                    else:
                        target_signature = SIGNATURES[format]['header']
                    
                    position_header = data.find(target_signature, search_pointer) #finding the signature of the formats
                    
                    if position_header == -1:
                        print(f"No more {format} in buffer") #if no more headers are found, break and go to next format
                        break


                    if format == "mp4":
                        abs_start = actual_position + position_header - 4 #the headers of mp4 files are 4 bytes before ftyp
                    else:
                        abs_start = actual_position + position_header

                    #Here we will begin the extraction process for files
                    if format == "mp4":
                        if carve_mp4(i, outpath, abs_start, f):
                            i = i+1
                        search_pointer = position_header + 4
                        
                    elif format == "zip":
                        if carve_zip(i, outpath, abs_start, f):
                            i = i+1
                        search_pointer = position_header + 4

                    else:
                        position_footer = data.find(SIGNATURES[format]['footer'], position_header + len(target_signature))
                        
                        if position_footer != -1: #if footer is found
                            footer_len = len(SIGNATURES[format]['footer'])
                            restored_raw_file = data[position_header : position_footer + footer_len]
                            
                            name = f"restored_{i}.{SIGNATURES[format]['extension']}"
                            with open(os.path.join(outpath, format, name), 'wb') as rf:
                                rf.write(restored_raw_file)
                            print(f"Success: {format}_{i} extracted with success!")
                            
                            i = i+1 #counting the number of extracted files
                            search_pointer = position_footer + footer_len #updating the search pointer for the next file
                        else:
                            #if footer is not found, fuck off and go to the next header
                            search_pointer = position_header + len(target_signature)

            progress.update(len(data))

def main():
    print_welcome()
    if len(sys.argv) < 3:
        console.print("Usage: python3 lawliet.py \"isopath\" \"outpath\" -b \"buffer_size (in MB)\"")
        console.print("Buffer size parameter is optional")
        console.print("Default buffer size is 8MB")
        sys.exit()
    
    if len(sys.argv) == 5 and sys.argv[3] == "-b": #Yeah i know it's not the best way but it works
        buffer_size = int(sys.argv[4])*1024*1024
    else:
        buffer_size = 8*1024*1024
    carve(sys.argv[1], sys.argv[2], buffer_size)
    console.print("Carving process finished")
    sys.exit()

if __name__ == "__main__":
    main()
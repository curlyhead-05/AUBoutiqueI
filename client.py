import socket
import json
import threading 

stopThreading = False
messages = []

def connectToServer():
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.connect((socket.gethostbyname(socket.gethostname()),8005))
    return clientSocket

def sendRequest(clientSocket, request):
    
    json_request = json.dumps(request)
    clientSocket.sendall(json_request.encode('utf-8'))
    
    json_response = clientSocket.recv(1024).decode('utf-8')
    
    if not json_response: 
       raise ValueError("Empty response from server")
       
    response = json.loads(json_response)
    return response

def register(clientSocket):
    
    clientName = input("Enter name: ")
    clientEmail = input("Enter email: ")
    clientUsername = input("Enter username: ")
    clientPassword = input("Enter password: ")
    
    request = {"action": "register", "userName": clientName, "userEmail": clientEmail, "userUsername": clientUsername, "userPassword": clientPassword}
    
    response = sendRequest(clientSocket, request)
    
    print(response['message'])
    
def login(clientSocket):
    
    global stopThreading
    
    userUsername = input("Enter username: ")
    userPassword = input("Enter password: ")
    
    request = {"action": "login", "userUsername": userUsername, "userPassword": userPassword}
    
    try:
        response = sendRequest(clientSocket, request)
    
        if response['status'] == 'success':
            print(response['message'])
            
            stopThreading = False
            thread = threading.Thread(target=listenForMessages, args=(clientSocket,))
            thread.daemon = True
            thread.start()
            
            return response["userId"], response.get('products', [])
    
        else:
            print("Login failed: ", response['message'])
            return None
        
    except Exception as e:
        print("An error occurred during login:", str(e))
        return None

def listProducts(clientSocket):
    request = {"action":"listProducts"}
    
    try: 
        response = sendRequest(clientSocket,request)
    
        if response["status"] == "success": 
            if response["products"]:
                print("Products available:")
                
                for product in response["products"]:
                    print(f"ID: {product['productId']}")
                    print(f"Name: {product['productName']}")
                    print(f"Description: {product['productDescription']}")
                    print(f"Price: ${product['productPrice']:.2f}")
                    print(f"Owner ID: {product['ownerId']}")
            else:
                print("No available products to show.")
             
        else:
            print("Error:", response["message"])
            
    except Exception as e:
        print("An error occurred while listing the products: ", str(e))
        
def viewProductsByOwner(clientSocket):
    ownerId = int(input("Enter the owner's ID: "))
    request = {"action": "viewProductsByOwner", "ownerId": ownerId}
    
    response = sendRequest(clientSocket, request)
    if response["status"]=="success":
        print(f"Products by owner {ownerId}: ")

        for product in response["products"]: 
            print(f"ID: {product['productId']}")
            print(f"Name: {product['productName']}")
            print(f"Description: {product['productDescription']}")
            print(f"Price: ${product['productPrice']:.2f}")
    else:
        print("Error:", response["message"])
        
def checkOnlineStatus(clientSocket):
    ownerId = input("Enter the owner's ID: ")
    request = {"action":"checkOnlineStatus", "ownerId": ownerId}
    
    response = sendRequest(clientSocket, request)
    
    if response["status"] == "success":
        
        if response["userOnline"]:
            status = "online"
            
        else:
            status = "offline"
            
        print(f"{ownerId} is currently {status}.")
        return response["userOnline"]
    else:
        print(response["message"])
        return None

def addProduct(clientSocket,userId):
    productName = input("Enter product name: ")
    productPrice = float(input("Enter price: "))
    productDescription = input("Enter description: ")
    imagePath = input("Enter image: ")

    request = {"action": "addProduct", "userId": userId, "productName": productName, "productPrice": productPrice, "productDescription": productDescription, "imagePath": imagePath}
    response = sendRequest(clientSocket, request)
    print(response['message'])

def buyProduct(clientSocket,userId):
    productId = int(input("Enter the ID of the product you wish to buy: "))
    request = {"action":"buyProduct","userId": userId, "productId": productId}
    
    response = sendRequest(clientSocket, request)
    print(response["message"])
    
def viewBuyers(clientSocket):
    productId = int(input("Enter your product ID to view buyer: "))
    request = {"action": "viewBuyers", "productId": productId}
    
    response = sendRequest(clientSocket, request)
    
    if response["status"] == "success":
       print(f"The buyer of product {productId} is {response['buyer']}.")
       
    else:
       print(response["message"])
       
def sendMessage(clientSocket):
    ownerUsername = input("Enter the owner's username: ")
    
    onlineStatus = checkOnlineStatus(clientSocket)
    
    if onlineStatus:
        message = input("Enter your message: ")
        request = {"action": "sendMessage", "recipient": ownerUsername, "message": message}
        
        response = sendRequest(clientSocket, request)
        print(response["message"])
        
    elif onlineStatus == False:
        print(f"Cannot send message, {ownerUsername} is offline.")
        
    else:
        print("Owner not found")

def displayIncomingMessages():
    
    if messages:
        print("Incoming Messages: ")
        
        for message in messages:
            print(messages.pop(0))
            
        messages.clear()
        
    else:
        print("No new messages.")
    
def listenForMessages(clientSocket):
    
    global stopThreading
    
    clientSocket.settimeout(5)
    
    while not stopThreading:
        try:
            json_response = clientSocket.recv(1024).decode('utf-8')
           
            if json_response:
                response = json.loads(json_response)
                
                if response['status'] == 'success' and 'from' in response and 'message' in response:
                    #print(f"\nMessage from {response['from']}: {response['message']}")
                    messages.append(f"Message from {response['from']}: {response['message']}")
        
        except socket.timeout:
            continue
        
        except Exception as e:
            print("An error occurred while receiving messages:", str(e))
            break

def displayMainMenu():
    print("1. Register")
    print("2. Already registered? Login here!")
    print("3. Exit")

def displayUserMenu():
    print("1. List Products")
    print("2. View Products by Owner")
    print("3. Check Owner Online Status")
    print("4. Add Product")
    print("5. Buy Product")
    print("6. View Buyers")
    print("7. Send Message")
    print("8. Display Incoming Messages")
    print("9. Logout")

def main():
    
    global stopThreading

    clientSocket = connectToServer()
    
    try:
        while True:

            displayMainMenu()
            
            try: 
                clientInput = int(input("Choose an option: "))
            except ValueError:
                print("Invalid input! Please enter a number.")
            
            if clientInput == 1:
                register(clientSocket)
            
            elif clientInput == 2:
                loginResult  = login(clientSocket)
                
                if loginResult :
                    
                    userId, Products = loginResult
                    
                    listProducts(clientSocket)
                    
                    while True:
                        
                        displayUserMenu()
                        
                        userChoice = input("Choose an action: ")
                        
                        if userChoice == '1':
                            listProducts(clientSocket)
                        
                        elif userChoice == '2':
                            viewProductsByOwner(clientSocket)
                        
                        elif userChoice == '3':
                            checkOnlineStatus(clientSocket)
                        
                        elif userChoice == '4':
                            addProduct(clientSocket, userId)
                        
                        elif userChoice == '5':
                            buyProduct(clientSocket, userId)
                            
                        elif userChoice == '6':
                            viewBuyers(clientSocket) 
                            
                        elif userChoice == '7':
                            
                            if stopThreading:
                                print("You have been logged out.")
                                break
                            sendMessage(clientSocket)
                            
                        elif userChoice == '8':
                            displayIncomingMessages()
                
                        elif userChoice == '9':
                            print("Logging out...")
                            stopThreading = True
                            break
                        
                        else:
                            print("Invalid choice.")
                     
            elif clientInput == 3:
                stopThreading = True
                print("Exiting the program.")
                break
            
            else:
                print("Invalid choice.")
 
    finally:
        stopThreading = True
        clientSocket.close()

main()
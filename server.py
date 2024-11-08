import socket
import threading
import sqlite3
import json

connectedUsers = {}

def setupDatabase():
    db = sqlite3.connect("auboutique.db",check_same_thread=False)
    cursor = db.cursor()
    
    cursor.execute('''
                   CREATE TABLE if not exists users(
                       userId INTEGER PRIMARY KEY AUTOINCREMENT,
                       userUsername TEXT ,
                       userPassword TEXT,
                       userName TEXT,
                       userEmail TEXT, 
                       userOnline INT)
                   ''') 
                   
    cursor.execute('''
                   CREATE TABLE if not exists products(
                       productId INTEGER PRIMARY KEY AUTOINCREMENT,
                       ownerId INT, 
                       productName TEXT,
                       productDescription TEXT, 
                       productPrice REAL, 
                       imagePath TEXT, 
                       buyerId INT)
                   ''')
    db.commit()
    
    
    return db

def registerUser(request,cursor,db):
    try:
        userName = request['userName']
        userEmail = request['userEmail']
        userUsername = request['userUsername']
        userPassword = request['userPassword']

        cursor.execute("INSERT INTO users(userName,userEmail,userUsername,userPassword,userOnline) VALUES (?,?,?,?,?)" , (userName, userEmail, userUsername, userPassword,0))
        db.commit()
        return {"status": "success", "message": "Registration successful!"}
    
    except sqlite3.IntegrityError:
       return {"status": "error", "message": "Username or email already taken. Try again!"}
   
def loginUser(request,cursor,db):
    
    try:
        userUsername = request['userUsername']
        userPassword = request['userPassword']

        if not userUsername or not userPassword:
            return {"status": "error", "message": "Username or password missing"}

        cursor.execute("SELECT userId FROM users WHERE userUsername=? AND userPassword=?", (userUsername, userPassword))
        user = cursor.fetchone()
        
        if user is not None:
            cursor.execute("UPDATE users SET userOnline = 1 WHERE userId=?", (user[0],))
            db.commit()
            return {"status": "success", 'message': 'Login successful! Welcome to AUBoutique!', "userId": user[0],"userUsername": userUsername}
        else:
            return {"status": "error", "message": "Invalid username or password"}

    except Exception as e:
        print(f"Error during login processing: {e}")
        return {"status": "error", "message": "An error occurred during login."}

def listProducts(cursor):
    cursor.execute("SELECT products.productId, products.productName, products.productDescription, products.productPrice, users.userId FROM products JOIN users ON products.ownerId = users.userId WHERE products.buyerId IS NULL")
    products = cursor.fetchall()
    productsList = []
    
    for p in products: 
        productDetails = {"productId": p[0], "productName": p[1], "productDescription": p[2], "productPrice": p[3], "ownerId": p[4]}
        productsList.append(productDetails)
    
    return {"status":"success","products":productsList}

def updateUserStatus(userId, userStatus, cursor, db):
    cursor.execute("UPDATE users SET userOnline = ? WHERE userId = ?", (userStatus, userId))
    db.commit()

def viewProductsByOwner(request, cursor):
    ownerId = request['ownerId']  
    cursor.execute("SELECT productId, productName, productDescription, productPrice FROM products WHERE ownerId = ? AND buyerId IS NULL", (ownerId,))
    products = cursor.fetchall()
    
    productsList = []
    for p in products: 
        productDetails = {"productId": p[0], "productName": p[1], "productDescription": p[2], "productPrice": p[3]}
        productsList.append(productDetails)
    
    return {"status":"success","products":productsList}

def checkOnlineStatus(request, cursor):
    cursor.execute("SELECT userOnline FROM users WHERE userId = ?", (request['ownerId'],))
    status = cursor.fetchone()
    
    if status is not None:
        return {"status": "success", "userOnline": bool(status[0])}
    else:
        return {"status": "error", "message": "Owner not found"}

def addProduct(request,cursor,db):
    try:
        if request['productPrice'] < 0:
            return {"status": "error", "message": "Price must be a positive number."}
        
        cursor.execute("INSERT INTO products (ownerId, productName, productDescription, productPrice, imagePath) VALUES (?, ?, ?, ?, ?)", (request['userId'], request['productName'], request['productDescription'], request['productPrice'], request['imagePath']))
        db.commit()
        
        return {"status": "success", "message": "Product added successfully!"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

def buyProduct(request, cursor, db):
    try:
        cursor.execute("UPDATE products SET buyerId = ? WHERE productId = ?", (request['userId'], request['productId']))
        db.commit()
        return {"status": "success", "message": "Purchase confirmed. Please collect your product from the AUB Post Office on the specified date."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def viewBuyers(request, cursor):
    cursor.execute("SELECT users.userUsername FROM products JOIN users ON products.buyerId = users.userId WHERE products.productId = ?", (request['productId'],))
    buyer = cursor.fetchone()
    if buyer:
        return {"status": "success", "buyer": buyer[0]}
    else:
        return {"status": "error", "message": "No buyer found for this product."}   

def sendMessage(request, senderUsername):
    
    if 'recipient' not in request or 'message' not in request:
        return {"status": "error", "message": "Recipient and message must be provided."}
    
    recipientUsername = request['recipient']
    message = request['message']
    
    if recipientUsername in connectedUsers:
        recipientConnection = connectedUsers[recipientUsername]
        
        response = {"status": "success", "from": senderUsername, "message": message}
        json_response = json.dumps(response)
        
        try:
            recipientConnection.sendall(json_response.encode('utf-8'))

        except Exception as e:
            return {"status": "error", "message": f"Failed to send message: {str(e)}"}
        
        return {"status": "success", "message": "Message sent."}
        
    else:
        return {"status": "error", "message": "User is not online."}

def handleClient(connection,address):
    
    db = sqlite3.connect("auboutique.db",check_same_thread=False)
    cursor = db.cursor()
    
    
    print(f"Connection from {address} has been established!")
    
    currentUserId = None
    currentUsername = None
    
    try:
       while True:
            data = connection.recv(1024).decode('utf-8')
            
            if not data:
                print("No data recieved!")
                break
            
            print(f"Received: {data}")
            
            request = json.loads(data)
            
            if request['action'] == 'register':
                response = registerUser(request, cursor, db)
                
            elif request['action'] == 'login':
                response = loginUser(request, cursor, db)
                
                if response["status"] == "success":
        
                    currentUserId = response["userId"]
                    currentUsername = response["userUsername"]
                    
                    updateUserStatus(currentUserId, 1, cursor, db)
                    connectedUsers[currentUsername] = connection
                    
                    print(f"Login successful for user: {currentUsername}, UserId: {currentUserId}")
                    print(f"Current connected users: {connectedUsers}")
                    
                    response['products'] = listProducts(cursor)
                    
                else:
                    print("Login failed:", response["message"])
                    
            elif request['action'] == 'listProducts':
                response = listProducts(cursor)
            
            elif request['action'] == 'viewProductsByOwner':
                response = viewProductsByOwner(request, cursor)
               
            elif request['action'] == 'checkOnlineStatus':
                response = checkOnlineStatus(request, cursor)
                
            elif request['action'] == 'addProduct':
                response = addProduct(request, cursor,db)
            
            elif request['action'] == 'buyProduct':
                response = buyProduct(request, cursor,db)
            
            elif request['action'] == 'sendMessage':
                response = sendMessage(request,currentUsername)
                
            elif request['action'] == 'viewBuyers':
                response = viewBuyers(request, cursor)
            
            else:
                response = {"status": "error", "message": "Invalid action"}
                
            connection.sendall(json.dumps(response).encode('utf-8'))
            
    except Exception as e:
        response = {"status": "error", "message": str(e)}
        print(f"Error handling request from {address}: {e}")
        connection.sendall(json.dumps(response).encode('utf-8'))
        
    finally:
        if currentUserId:
            updateUserStatus(currentUserId, 0, cursor, db)  
            if currentUsername in connectedUsers:
                del connectedUsers[currentUsername]
                
        connection.close()
        print(f"Connection with {address} closed.")
        db.close()
        
def startServer():
    db = setupDatabase()
    serverSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    serverSocket.bind((socket.gethostbyname(socket.gethostname()),8005))
    serverSocket.listen()
    print("Server is listening on port 8005")
    
    try:
        while True: 
            try: 
                conn , addr = serverSocket.accept()
                print(f'Accepted connection from {addr}')
                thread = threading.Thread(target=handleClient, args = (conn, addr))
                thread.start() 
            except Exception as e:
                print(f"Error accepting connection: {e}")
    finally:
        serverSocket.close()
        db.close()
        print("Server shutdown.")

startServer()
    
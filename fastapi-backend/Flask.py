from flask import Flask, request, jsonify #jsonify used to create a response

app = Flask(__name__) #create flask applicaiton

"""
GET #request data from a source
POST #create a source
PUT #update a source
DELETE #delete a source
"""

@app.route("/") #this is a decorative, use the same name that defined flask application
def home(): #an endpoint, location on API to get some data
    return "Home"

@app.route("/get_user/<user_id>")
def get_user(user_id): #accept variable inside funciton parameter with the same name as the variable in the URL
    user_data = {
        "user_id": user_id,
        "name": "John Doe",
        "email": "john.doe@example.com"
    }
    extra = request.args.get("extra") #request.args is a dictionary of the query parameters
    if extra:
        user_data["extra"] = extra #add extra to the user_data dictionary
    return jsonify(user_data), 200 #200 is the status code for success

if __name__ == "__main__":
    app.run(debug=True) #run app
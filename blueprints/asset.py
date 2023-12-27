from flask import Blueprint, request, render_template, redirect, jsonify
from datetime import datetime
import os
from werkzeug.utils import secure_filename # import filename
import json 

from models.shared import db
from  models.service import Service
from .utilities import allowed_file, get_asset_upload_folder, get_image_upload_folder, get_attachment_upload_folder, delete_attachment_from_storage
from .configuration import app
from models.asset import Asset
from blueprints.utilities import retrieve_username_jwt
assets_blueprint = Blueprint('assets', __name__, template_folder='../templates')

def create_image(request_image, new_asset, asset_id):
    try:
        if 'image' in request_image:
            file = request_image.get('image')  # get the file from element 'image'
            # If the user does not select a file, the browser submits an empty file without a filename
            if file.filename == '':
                print('No selected file')  # no selected file
            if file and allowed_file(file.filename):  # if there is a file and it passes the allowed_file function
                filename = secure_filename(file.filename)  # get filename
                image_upload_folder = get_image_upload_folder(asset_id)  # call get_image_upload_folder and apss asset id
                if not os.path.exists(image_upload_folder): # if path doesn't exist 
                    os.makedirs(image_upload_folder) # then create

                file.save(os.path.join(image_upload_folder, filename))  # place file in folder
                new_asset.image_path = (os.path.join(image_upload_folder, filename))  # Save the image path to the database
    except Exception as e:
        print(f"Error uploading image: {e}")
    return new_asset
 

def create_asset(request_dict: dict, user_id: str, request_image: dict):
    name = request_dict.get('name') # get the name from form element 'name'
    asset_sn = request_dict.get('asset_sn') # get the asset sn from form 'easset_sn'
    description = request_dict.get('description') # get the description from form element 'desription'
    acquired_date = request_dict.get('acquired_date') # get the acquired_date from form element 'acquired_date'
    # Check if the necessary fields are provided
    if name and asset_sn: # required fields
        if acquired_date: # optional
            acquired_date = datetime.strptime(acquired_date, '%Y-%m-%d').date() #change to python
        else:
            acquired_date = None  # change to None
        new_asset = Asset(name=name, asset_sn=asset_sn, description=description, acquired_date=acquired_date, user_id=user_id) # make new_asset and is ready for adding to DB
        db.session.add(new_asset)  # Add new_asset to Class Assets
        db.session.commit()  # Commit changes to DB (saving it)
        new_asset = create_image(request_image, new_asset, asset_id=new_asset.id)
        db.session.add(new_asset) # Add new_asset to Class Assets
        db.session.commit() # Commit changes to DB (saving it)

@assets_blueprint.route('/asset_add', methods=['GET', 'POST']) # asset_add.html route
def add():
    """Api endpoint that creates a asset
    This api creates an asset, using the get route will render in the web ui
    ---
    tags:
      - assets
    consumes:
        - multipart/form-data
    produces:
        - application/json
    parameters:
        -  in: formData
           name: file
           required: true
           description: file to upload
           type: file
        
        -  in: formData
           name: name
           type: string
           example: asset1

        -  in: formData
           name: asset_sn
           type: string
           example: asset1

        -  in: formData
           name: description
           type: string
           example: description
        
        -  in: formData
           name: jwt
           type: string
           example: jwt
        
        -  in: formData
           name: acquired_date
           type: string
           example: 2023-10-11
    responses:
        200:
            description: Asset is created
        405:
            description: Error occured
    """
    if request.method == 'POST':
        if(request.form.get('jwt') == None):
            request_dict = {'meta_data': request.form, 'image': request.files['image']}
            user_id = retrieve_username_jwt(request.cookies.get('access_token'))
            create_asset(request_dict.get('meta_data'), user_id, request_dict)
            return render_template('asset_add.html', toast=True, loggedIn=True) # Display the toast message when add is commited to Class Assets
        else:
            request_dict = {'meta_data': request.form, 'image': request.files.getlist('file')[0]}
            user_id = retrieve_username_jwt(request.form.get('jwt'))
            create_asset(request_dict.get('meta_data'), user_id, request_dict)
            return {'message': f'Successfully created asset {request.form.get("name")}', 'status_code': 200}
        
    return render_template('asset_add.html', loggedIn=True) # display asset_add.html
    
@assets_blueprint.route('/asset_edit/<int:asset_id>', methods=['GET', 'POST'])  # asset_edit.html route
def edit(asset_id):
    if request.args.get('jwt') is None:
        asset = Asset.query.get_or_404(asset_id)  # query or get 404
        services = Service.query.filter_by(asset_id=asset_id).all()  # Fetch services associated with the asset
        
        if request.method == 'POST':  # if write
            name = request.form.get('name')  # get the name
            asset_sn = request.form.get('asset_sn')  # get the sn
            description = request.form.get('description')  # get description
            acquired_date = request.form.get('acquired_date')  # get the acquired date
            new_image_path = None
            # Check if the necessary fields are provided
            if name and asset_sn:  # required fields
                if acquired_date:  # optional
                    acquired_date = datetime.strptime(acquired_date, '%Y-%m-%d').date()  # change to python
                else:
                    acquired_date = None  # change to None
                asset.name = name  # set name
                asset.asset_sn = asset_sn  # set sn
                asset.description = description  # set asset
                try:
                    # Handle image upload
                    if 'image' in request.files:
                        image_path = asset.image_path  # get the image path
                        file = request.files['image']  # get the file from element 'image'
                        # If the user does not   select a file, the browser submits an empty file without a filename
                        if file.filename == '':  # Check if the name is blank
                            print('No selected file')  # no selected file
                        if file and allowed_file(file.filename):  # if there is a file and it passes the allowed_file function
                            filename = secure_filename(file.filename)  # get filename
                            new_image_path = get_image_upload_folder(asset_id)  # call get_image_upload_folder and apss asset id
                            if not os.path.exists(new_image_path): # if path doesn't exist 
                                os.makedirs(new_image_path) # then create
                            file.save(os.path.join(new_image_path, filename))  # place file in folder
                            image_path = os.path.join(new_image_path, filename)  # Save the image path to the database
                            asset.image_path = image_path # save iage path back to the asset image path
                except:
                    pass
                db.session.commit()  # commit changes
            return render_template('asset_edit.html', asset=asset, services=services, toast=True, loggedIn=True)  # if committed load asset_edit.html and send asset and services and call toast
    else:
        pass
    return render_template('asset_edit.html', asset=asset, services=services, toast=False, loggedIn=True)  # if committed load asset_edit.html and send asset and services and NO BUTTER TOAST

@assets_blueprint.route('/asset_all', methods=['GET']) # asset_all.html route
def all_assets():
    """Api endpoint that gets all assets
    This api gets all assets associated with a user
    ---
    tags:
      - assets
    parameters:
        - in: body
          name: body
          required: true 
          example: {'jwt': 'test'}
    responses:
        200:
            description: All assets are retrived
        405:
            description: Error occured
    """
    if request.args.get('jwt') is None:
        user_id = retrieve_username_jwt(request.cookies.get('access_token'))
        assets = Asset.query.filter_by(user_id=user_id).all() # query all in class Asset
        return render_template('asset_all.html',assets=assets, loggedIn=True) # display asset_all.html and pass assets
    else:
        user_id = retrieve_username_jwt(request.json.get('jwt'))
        assets = Asset.query.filter_by(user_id=user_id).all() # query all in class Asset
        data = []
        for asset in assets:
            asset_data = {
                'name': asset.name,
                'asset_sn': asset.asset_sn,
                'description': asset.description,
                'acquired_date': str(asset.acquired_date),
                'image_path': asset.image_path
            }
            data.append(asset_data)
        return json.dumps(data)

def delete_asset_helper(asset_id, user_id):
    asset = Asset.query.get_or_404(asset_id) # get asset by id
    
    # Check if the asset has associated services
    if asset.services: # If yes, delete the associated services first
        for service in asset.services:
            if service.serviceattachments and service.user_id == user_id: # If yes, delete the associated attachments first
                for attachment in service.serviceattachments: # Delete the file from your storage 
                    delete_attachment_from_storage(attachment.attachment_path) # Delete the attachment record from the database
                db.session.delete(attachment) # delete attachment
            db.session.delete(service) # delete service
    db.session.delete(asset) # Delete the asset
    db.session.commit() # Commit the changes

@assets_blueprint.route('/asset_delete/<asset_id>', methods=['POST']) # route for delete an asset by id
def delete_asset(asset_id):
    """Api endpoint that deletes a asset
    This api deletes an asset
    ---
    tags:
      - assets
    parameters:
        - in: body
          name: body
          required: true 
          example: {'asset_id': 'test', 'jwt': 'test'}
    responses:
        200:
            description: Asset is deleted
        405:
            description: Error occured
    """
    
    if request.args.get('jwt') != None:
        user_id = retrieve_username_jwt(request.cookies.get('access_token'))
        delete_asset_helper(asset_id, user_id)
        return redirect('/home') # display index.html
    else:
        user_id = retrieve_username_jwt(request.json.get('jwt'))
        asset_id = request.json.get('asset_id')
        delete_asset_helper(asset_id, user_id)
        return {'message': f'Successfully delete asset {request.json.get("asset_id")}', 'status_code': 200}
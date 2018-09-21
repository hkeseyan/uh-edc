# if the access file has its columns reorganized the load_Metadata_Page() method needs to have
# the elements renumbered appropriate


from flask import Flask, render_template, request, flash, session, url_for, redirect
import flask
import os
from flask_uploads import UploadSet, configure_uploads, IMAGES
from datetime import datetime
from flask_wtf import form
import pypyodbc
import re
from static.FieldName import Field, DataForm, SearchHit

app = Flask(__name__)

# flask.g[0] = (string) | MetadataID, flask.g[1] = (boolean) | was update clicked?
flask.g = [None, None]

connect = pypyodbc.connect(r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
                        r'DBQ=C:\Users\AR42\PycharmProjects\Data Hub\Metadata.accdb;')
cursor = connect.cursor()
# cursor.execute('CREATE TABLE `Organizations` (`id` INTEGER NOT NULL, `name` VARCHAR(200)NOT NULL, primary key(`id`));')
# sql = "ALTER TABLE [Metadata] ADD [CodeLibrary] VARCHAR(255);"
# cursor.execute(sql).commit()
# sql = "ALTER TABLE [Metadata] ADD [OwnerEmail] VARCHAR(100);"
# cursor.execute(sql).commit()
# sql = "DELETE * FROM Metadata"
# sql = "DELETE * FROM FieldNames"
# cursor.execute(sql).commit()
# sql = "DELETE * FROM Tags"
# cursor.execute(sql).commit()

# rows = cur.execute('SELECT `name` FROM `t3` WHERE `id` = 3')

photos = UploadSet('photos', IMAGES)

app.config['UPLOADED_PHOTOS_DEST'] = 'static/img'
configure_uploads(app, photos)


# for use in debugging the jinja code. Use {{ debug(string) }} in the html to call function
def debug(text):
    print(text)
    return ''


def type_jinja(object):
    if type(object) == DataForm:
        return'DataForm'
    elif type(object) == Field:
        return 'Field'
    else:
        return 'None'

# places the function to be used in jinja
app.jinja_env.globals.update(debug=debug)
app.jinja_env.globals.update(type_jinja=type_jinja)


# configures the flask form key to be used
app.config.update(dict(
    SECRET_KEY="dfsdfdfsecret1234567890key",
    WTF_CSRF_SECRET_KEY="what is a csrf key doing here?"
))


# displays the home page with buttons for metadata form and profile page
# with the option of going to a specific profile page based on metadata id number
# (Button) : (Description)
# New Metadata Form : redirects to a blank metadata form page that can be filled out
# Blank Profile Page : redirects to the profile page and loads no data
@app.route('/', methods=['POST', 'GET'])
def home_page():
    data_form = DataForm()
    data_form.multipleFields.clear()
    data_form.organizations = load_organization_list()
    flask.g = [None, None]
    error = None
    if request.method == 'POST':
        if request.form['Button'] == 'New Metadata Form':
            return redirect(url_for("metadata_page", data_form=data_form))
        elif request.form['Button'] == 'Blank Profile Page':
            flask.g[0] = None
            return redirect(url_for('profile_page', id=" "))
        elif request.form['Button'] == 'search':
            search_list = search(request.form['search'])
            results = load_search_results(search_list)

            return render_template("Home.html", results=results , searching=True)
    return render_template("Home.html", searching=False)


# profile_page( string| id)
# will load the id into flask.g as D### to be used to find the metadata
# (Button) : (Description)
# Back : redirects to the homepage
# Update : sets flask.g[1] to True and redirects to the Metadata page that will have the data for the ID in flask.g[0]
# Upload Image: will save the img in the file input bar the the static/img folder then save the filename to the
#               Metadata row and redirects so the image will be displayed in the profile.
#               only one image will be saved at a time and it will delete the previous image in the static/img folder
@app.route('/Profile/<string:id>', methods=['POST', 'GET'])
def profile_page(id):
    flask.g[1] = False
    if id != ' ' and id != '':
        flask.g = [('D' + id), True]
    if flask.g[0] is not None and flask.g[0] != '':
        data_form = load_Metadata_Page(flask.g[0])
    else:
        data_form = DataForm()

    if request.method == 'POST':
        if request.form['Button'] == 'Back':
            flask.g[0] = None
            return redirect(url_for('home_page'))
        elif request.form['Button'] == 'Update':
            flask.g[1] = True
            return redirect(url_for("metadata_page", data_form=data_form))
        elif request.form['Button'] == 'Upload Image' and 'photo' in request.files:
            filename = photos.save(request.files['photo'])
            sql_select = "SELECT Image FROM Metadata WHERE MetadataID = " + flask.g[0][1:] + ";"
            old_img = cursor.execute(sql_select).fetchone()[0]
            if old_img is not None:
                print('old_img is not none')
                print("old_img = /static/img/" + old_img)
                os.remove("static/img/" + old_img)

            sql_update = "UPDATE MetaData SET Image = ? WHERE MetadataID = " + flask.g[0][1:] + ";"
            cursor.execute(sql_update, [filename]).commit()
            return redirect('/Profile/' + id)

    return render_template('Profile.html', data_form=data_form)


# metadata_page()
# the metadata form page provides functionality to the input buttons on the page
# (Button) : (Description)
# Field Data : saves the metadata entered in the text boxes into the metadata table and creates the field names in the
#               field names table
# Cancel : will delete all data associated with the current dataset in flask.g and redirect to the home page
#           or redirect to the profile page if in update
@app.route('/metadataForm', methods=['POST', 'GET'])
def metadata_page():
    data_form = DataForm()
    data_form.organizations = load_organization_list()
    if request.method == 'POST':
        if request.form['Button'] == 'Field Data':
            pattern_phone = re.compile("^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$")
            pattern_email = re.compile("^(([^<>()\[\]\.,;:\s@\"]+(\.[^<>()\[\]\.,;:\s@\"]+)*)|(\".+\"))@(([^<>()[\]\.,;:\s@\"]+\.)+[^<>()[\]\.,;:\s@\"]{2,})$")
            checkbox = False
            if 'accessControl' in request.form:
                checkbox = True
            frequency = ''
            if request.form['frequencyIngestRate'] == 'Other':
                frequency = request.form['frequencyOther']
            else:
                frequency = request.form['frequencyIngestRate']
            organization = request.form['OrganizationSearchAdd']
            organizations_list_insert(organization)

            params = (request.form['dataOwnerName'],            #0
                      organization,                             #1
                      request.form['analystName'],              #2
                      request.form['interviewerName'],          #3
                      request.form['guidanceInAcquiring'],      #4
                      request.form['format'],                   #5
                      request.form['dataSize'] + request.form['dataSizeType'],#6
                      frequency,                                #7
                      request.form['sourceOfData'],             #8
                      request.form['versionControl'],           #9
                      request.form['archivingRules'],           #10
                      request.form['headerInformation'],        #11
                      request.form['metricsCollected'],         #12
                      request.form['metricsToCollect'],         #13
                      request.form['dataDependencies'],         #14
                      request.form['actionsTaken'],             #15
                      checkbox,                                 #16
                      request.form['verificationOfData'],       #17
                      request.form['concerns'],                 #18
                      request.form['SCG'],                      #19
                      request.form['distributionStatement'],    #20
                      request.form['tags'],                     #21
                      request.form['fieldNames'],               #22
                      request.form['dataSetName'],              #23
                      request.form['dataOwnerPhone'],           #24
                      request.form['dataOwnerEmail'],           #25
                      request.form['codeLibrary'])              #26

            if request.form['dataSetName'] == '':
                error = u'dataSetNameNonexistent'
                data_form = convert_to_data_form(params)
                flash(error, 'error')
                return render_template("MetadataForm.html", error=error, data_form=data_form)
            elif in_table('Metadata', 'DataSetName', "'" + request.form['dataSetName'] + "'") and not flask.g[1]:
                error = u'dataSetNameAlreadyExists'
                data_form = convert_to_data_form(params)
                flash(error, 'error')
                return render_template("MetadataForm.html", error=error, data_form=data_form)
            elif pattern_phone.match(request.form['dataOwnerPhone']) is None and request.form['dataOwnerPhone'] != '':
                error = u'InvalidPhone'
                data_form = convert_to_data_form(params)
                flash(error, 'error')
                return render_template("MetadataForm.html", error=error, data_form=data_form)

            elif pattern_email.match(request.form['dataOwnerEmail']) is None and request.form['dataOwnerEmail'] != '':
                error = u'InvaildEmail'
                data_form = convert_to_data_form(params)
                flash(error, 'error')
                return render_template("MetadataForm.html", error=error, data_form=data_form)

            else:
                if flask.g[0] is None:
                    insert_Metadata(params)
                else:
                    check_tags_delete_missing(request.form['tags'], 'Metadata', 'MetadataID', flask.g[0])
                    update_Metadata(params)
                data_form = insert_fields_from_textarea(data_form)
                data_form = load_Metadata_Page(flask.g[0])
                tag_list = request.form['tags'].split(';')
                for tags in tag_list:
                    insert_tag(tags, flask.g[0])
                    more_tags = tags.split(' ')
                    for tag_from_space in more_tags:
                        if tag_from_space != '':
                            insert_tag(tag_from_space, flask.g[0])
                update_metadata_fields_string()
                return render_template('FieldForm.html', data_form=data_form)
        elif request.form['Button'] == 'Cancel':
            if flask.g[0] is not None:
                if flask.g[1]:
                    return redirect('/Profile/' + flask.g[0][1:])
                else:
                    return cancel_form()
            else:
                return redirect(url_for("home_page"))
    if flask.g[0] is None:
        return render_template("MetadataForm.html", data_form=data_form)
    elif flask.g[0] is not None:
        update_metadata_fields_string()
        return render_template("MetadataForm.html", data_form=load_Metadata_Page(flask.g[0]))


# field_page()
# displays the field names page and add functionality to input buttons on the page.
#  must be accessed through metadata form page
# (Button) : (Description)
# Add : inserts a Field name with entered data into the FieldNames table and adds it the list of current Field Names
# Delete Field : finds the field to be deleted based on data in hidden input then removes it from the list
#               and FieldNames table
# Submit : saves the data in the field form to the FieldNames page and creates a date stamp for the date created.
#           it will then display the success page to show completion
# Back : saves field names data to FieldNames table and returns to the metadata form page
@app.route('/FieldForm', methods=['POST', 'GET'])
def field_page():
    data_form = DataForm()
    if request.form['Button'] == 'Add':
        if request.form['addFieldName'] == '':
            error = u'addFieldNameNonexistent'
            flash(error, 'error')
            return render_template("FieldForm.html", error=error, data_form=data_form)

        new_field = Field()
        new_field.name = request.form['addFieldName']
        new_field.description = request.form['addFieldDescription']
        new_field.units = request.form['addFieldUnits']
        new_field.tags = request.form['addFieldTags']
        new_field.collapseButtonTargetID = "button" + request.form['addFieldName'] + \
                                           str(len(data_form.multipleFields) - 1)
        new_field.collapseButtonID = "buttonID" + request.form['addFieldName'] + str(len(data_form.multipleFields) - 1)
        new_field.nameID = request.form['addFieldName'] + str(len(data_form.multipleFields) - 1)
        new_field.descriptionID = "description" + request.form['addFieldName'] + str(len(data_form.multipleFields) - 1)
        new_field.unitsID = "units" + request.form['addFieldName'] + str(len(data_form.multipleFields) - 1)
        new_field.tagsID = "tags" + request.form['addFieldName'] + str(len(data_form.multipleFields) - 1)

        params = [flask.g[0], new_field.name, new_field.description, new_field.units, new_field.tags]

        new_field.fieldID = insert_FieldNames(params)

        data_form.multipleFields.append(new_field)
        update_metadata_fields_string()

        return render_template("FieldForm.html", data_form=data_form)
    elif request.form['Button'] == 'Delete Field':
        for fields in data_form.multipleFields:
            if fields.nameID == request.form['deleteField']:
                data_form.multipleFields.remove(fields)
                sql_select = "SELECT ID FROM FieldNames WHERE DataSet = '" + flask.g[0] + "' AND FieldName = '" + fields.name + "';"
                field_id = cursor.execute(sql_select).fetchone()[0]
                for tag in fields.tags.split(';'):
                    delete_tag(tag,field_id)

                sql_delete = "DELETE FROM FieldNames WHERE DataSet = ? AND FieldName = ?;"
                cursor.execute(sql_delete, [flask.g[0], fields.name]).commit()
                sql_select = "SELECT Fields FROM Metadata WHERE MetadataID = " + flask.g[0][1:] + ";"
                field_strings = cursor.execute(sql_select).fetchone()[0].split(';')

                newString = ''
                for value in field_strings:
                    if value == fields.name:
                        field_strings.remove(value)
                for values in field_strings:
                    newString += (values + ';')

                sql_update = "UPDATE Metadata SET Fields = '" + newString[:-1] + "' WHERE MetadataID = " + flask.g[0][
                                                                                                           1:] + ";"
                cursor.execute(sql_update).commit()

        return render_template("FieldForm.html", data_form=data_form)
    elif request.form['Button'] == 'Submit':
        for field in data_form.multipleFields:
            if request.form[field.nameID] == '':
                error = field.nameID
                collapseID = field.collapseButtonTargetID
                flash(error, 'error')
                return render_template("FieldForm.html", error=error, data_form=data_form, collapseID=collapseID)
            params = [flask.g[0], request.form[field.nameID], request.form[field.descriptionID],
                      request.form[field.unitsID], request.form[field.tagsID]]
            save_fields(params, field.fieldID)
            update_metadata_fields_string()

        date_stamp()
        return redirect(url_for("form_success"))
    elif request.form['Button'] == 'Back':
        for field in data_form.multipleFields:
            params = [flask.g[0], request.form[field.nameID], request.form[field.descriptionID],
                      request.form[field.unitsID], request.form[field.tagsID]]
            save_fields(params, field.fieldID)
            update_metadata_fields_string()
        return redirect(url_for("metadata_page", data_form=data_form))

    error = ''
    return render_template("FieldForm.html", data_form=load_Metadata_Page(flask.g[0]), error=error)


# form_success()
# a page to show that all the data was successfully submitted
@app.route('/FormSuccess', methods=['POST', 'GET'])
def form_success():
    if request.method == 'POST':
        if flask.g[1]:
            return redirect('/Profile/' + flask.g[0][1:])
        else:
            return redirect(url_for("home_page"))
    return render_template("FormSuccess.html")


# date_stamp()
# checks if metadata row has a created date stamp and if it doesn't it will save to the DateCreated column
# otherwise it will save the date stamp to the DateUpdated column
def date_stamp():
    sql_select = "SELECT DateCreated FROM Metadata WHERE MetadataID = " + flask.g[0][1:] + ";"
    check = cursor.execute(sql_select).fetchone()[0]
    if check == None or check == '':
        sql_update = "UPDATE Metadata SET DateCreated = '" + str(datetime.now().date()) + \
                     "' WHERE MetadataID = " + flask.g[0][1:] + ";"
        cursor.execute(sql_update).commit()
    else:
        sql_update = "UPDATE Metadata SET DateUpdated = '" + str(datetime.now().date()) + \
                     "' WHERE MetadataID = " + flask.g[0][1:] + ";"
        cursor.execute(sql_update).commit()


# clear_single_data( string| table, string| column)
# clear a single data point, parameters are the table and column of the data point
def clear_single_data(table, column):
    if flask.g[0] != None:
        sql_delete = "UPDATE " + table + " SET " + column + " = '' WHERE MetadataID = " + flask.g[0][1:] + ";"
        cursor.execute(sql_delete)


# save_fields( list[string]| params, string| field_id)
# cleans the field name and determines if the field name is to be inserted or updated
def save_fields(params, field_id):
    params[1] = clean_field_name(params[1])
    sql_select = "SELECT * FROM FieldNames WHERE ID =" + field_id[1:] + ";"
    if cursor.execute(sql_select).fetchone() is None:
        insert_FieldNames(params)
    else:
        update_FieldNames(params, field_id)


# load_Metadata_Page( string | MetadataID)
# loads all the data for the Metadata form page MetadataID is in format (D123)
def load_Metadata_Page(MetadataID):
    Form = DataForm()
    id_number = MetadataID[1:]
    sql_select = "SELECT * FROM Metadata WHERE MetadataID= " + id_number + ";"
    data = cursor.execute(sql_select).fetchall()

    Form.DataSetID = data[0][0]
    Form.DataOwnerName = data[0][1]
    Form.DataOwnerOrganization = data[0][2]
    Form.AnalystName = data[0][3]
    Form.InterviewerName = data[0][4]
    Form.GuidanceInAcquiringData = data[0][5]
    Form.Format = data[0][6]
    Form.TotalSize = data[0][7]
    Form.ArchivingRules = data[0][11]
    Form.Frequency = data[0][8]
    Form.Source = data[0][9]
    Form.Version = data[0][10]
    Form.Header = data[0][12]
    Form.Tags = data[0][22]
    Form.ActionsTaken = data[0][16]
    Form.MetricsCollected = data[0][13]
    Form.MetricsToCollect = data[0][14]
    Form.DataDependencies = data[0][15]
    Form.VerificationOfData = data[0][18]
    Form.SecurityConcerns = data[0][19]
    Form.SCG = data[0][20]
    Form.DistributionStatement = data[0][21]
    Form.FieldNames = data[0][23]
    Form.DataSetName = data[0][24]
    if data[0][25] is not None:
        Form.Created = data[0][25].date()
    if data[0][26] is not None:
        Form.LastUpdated = data[0][26].date()
    Form.DataOwnerPhone = data[0][27]
    Form.DataOwnerEmail = data[0][28]
    Form.CodeLibrary = data[0][29]
    Form.Image = data[0][30]

    Form.multipleFields.clear()

    sql_select = "SELECT * FROM FieldNames WHERE Dataset = '" + MetadataID + "';"
    if cursor.execute(sql_select).fetchall() != []:
        sql_select = "SELECT ID FROM FieldNames WHERE Dataset = '" + MetadataID + "';"
        fields_ids = cursor.execute(sql_select).fetchall()
        fields_ids_list = []
        for ids in fields_ids:
            fields_ids_list += [ids[0]]
        for ids in fields_ids_list:
            sql_select = "SELECT * FROM FieldNames WHERE ID= " + str(ids) + ";"
            field_data = cursor.execute(sql_select).fetchall()

            new_field = Field()
            new_field.fieldID = 'F' + str(ids)
            new_field.name = field_data[0][2]
            new_field.description = field_data[0][3]
            new_field.units = field_data[0][4]
            new_field.tags = field_data[0][5]
            new_field.collapseButtonTargetID = "button" + new_field.name + str(len(Form.multipleFields) - 1)
            new_field.collapseButtonID = "buttonID" + new_field.name + str(len(Form.multipleFields) - 1)
            new_field.nameID = new_field.name + str(len(Form.multipleFields) - 1)
            new_field.descriptionID = "description" + new_field.name + str(len(Form.multipleFields) - 1)
            new_field.unitsID = "units" + new_field.name + str(len(Form.multipleFields) - 1)
            new_field.tagsID = "tags" + new_field.name + str(len(Form.multipleFields) - 1)
            Form.multipleFields.append(new_field)

    Form = insert_fields_from_textarea(Form)

    Form.organizations = load_organization_list()

    return Form


# load_Metadata_searched(string | MetadataID)
# Uses the metadata ID to find the data in the database and loads it into
# a DataForm class object and returns it to be added into the results list
def load_Metadata_searched(MetadataID):
    Form = DataForm()
    id_number = MetadataID[1:]
    sql_select = "SELECT * FROM Metadata WHERE MetadataID= " + id_number + ";"
    data = cursor.execute(sql_select).fetchall()
    Form.DataSetID = data[0][0]
    Form.DataOwnerName = data[0][1]
    Form.DataOwnerOrganization = data[0][2]
    Form.AnalystName = data[0][3]
    Form.InterviewerName = data[0][4]
    Form.GuidanceInAcquiringData = data[0][5]
    Form.Format = data[0][6]
    Form.TotalSize = data[0][7]
    Form.ArchivingRules = data[0][11]
    Form.Frequency = data[0][8]
    Form.Source = data[0][9]
    Form.Version = data[0][10]
    Form.Header = data[0][12]
    Form.Tags = data[0][22]
    Form.ActionsTaken = data[0][16]
    Form.MetricsCollected = data[0][13]
    Form.MetricsToCollect = data[0][14]
    Form.DataDependencies = data[0][15]
    Form.VerificationOfData = data[0][18]
    Form.SecurityConcerns = data[0][19]
    Form.SCG = data[0][20]
    Form.DistributionStatement = data[0][21]
    Form.FieldNames = data[0][23]
    Form.DataSetName = data[0][24]
    if data[0][25] is not None:
        Form.Created = data[0][25].date()
    if data[0][26] is not None:
        Form.LastUpdated = data[0][26].date()
    Form.DataOwnerPhone = data[0][27]
    Form.DataOwnerEmail = data[0][28]
    Form.CodeLibrary = data[0][29]
    Form.Image = data[0][30]

    return Form


# load_organization_list()
# add data_owner_organizations to a list that will be loaded into the Metadata page
def load_organization_list():
    sql_select = "SELECT Organizations FROM Organizations "
    organizations_list = []
    for strings in cursor.execute(sql_select).fetchall():
        organizations_list += [strings[0]]
    return organizations_list


# insert_fields_from_textarea( DataForm| Form)
# creates and inserts the new field names that were entered in the text field
def insert_fields_from_textarea(Form):
    sql_select = "SELECT Fields FROM Metadata WHERE MetadataID= " + flask.g[0][1:] + ";"
    data = cursor.execute(sql_select).fetchone()[0]
    if data != '':
        fields_list = ''
        for field_name in data.split(';'):
            field_name = clean_field_name(field_name)
            fields_list += field_name + ';'

        for field_name in fields_list.split(';'):
            if field_name != '':
                sql_select = "SELECT * FROM FieldNames WHERE Dataset=? AND fieldName=?;"
                if cursor.execute(sql_select, params=[flask.g[0], field_name]).fetchone() is None:
                    insert_FieldNames([flask.g[0], field_name, '', '', ''])

        element_num = 0
        in_Form = False
        for field_name in fields_list.split(';'):
            if field_name != '':
                for names in Form.multipleFields:
                    if field_name == names.name:
                        in_Form = True
                if not in_Form:
                    sql_select = "SELECT ID FROM FieldNames WHERE DataSet='" + flask.g[0] + "' AND FieldName='" + field_name + "';"
                    field_id = cursor.execute(sql_select).fetchone()[0]
                    new_field = Field()
                    new_field.fieldID = 'F' + str(field_id)
                    new_field.collapseButtonTargetID = "button" + field_name + str(element_num)
                    new_field.collapseButtonID = "buttonID" + field_name + str(element_num)
                    new_field.nameID = field_name + str(element_num)
                    new_field.descriptionID = "description" + field_name + str(element_num)
                    new_field.unitsID = "units" + field_name + str(element_num)
                    new_field.tagsID = "tags" + field_name + str(element_num)
                    new_field.name = field_name
                    element_num += 1
                    Form.multipleFields.append(new_field)
    return Form


# insert_Metadata( list[string]| params)
# inserts a new row for the metadata that is entered
def insert_Metadata(params):
    sql_insert = "INSERT INTO Metadata (OwnerName, OwnerOrganization, AnalystName, InterviewerName , " \
                 "GuidanceInAcquiring, Format, TotalSize, Frequency, CollectionMethod, Version, ArchivingRules, " \
                 "Header, CurrentMetrics, MetricsToCollect, Dependencies, ActionsTaken, RequiresRequest, Validation, " \
                 "Concerns, SCG, DistributionStatement, Tags, Fields, DataSetName, OwnerPhone, OwnerEmail, CodeLibrary) " \
                 "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);"
    cursor.execute(sql_insert, params).commit()
    sql_id = "SELECT @@IDENTITY AS id;"
    pat = re.compile(r"""\d""")
    flask.g[0] = 'D'
    for ints in pat.findall(str(cursor.execute(sql_id).fetchone())):
        flask.g[0] += ints


# update_Metadata( list[string]| params)
# updates the data for existing Metadata row
def update_Metadata(params):
    id = flask.g[0][1:]
    sql_update = "UPDATE Metadata SET OwnerName = ?, OwnerOrganization = ?, AnalystName = ?, InterviewerName = ?, " \
                 "GuidanceInAcquiring = ?, Format = ?, TotalSize = ?, Frequency = ?, CollectionMethod = ?," \
                 " Version = ?, ArchivingRules = ?, Header = ?, CurrentMetrics = ?, MetricsToCollect = ?," \
                 " Dependencies = ?, ActionsTaken = ?, RequiresRequest = ?, Validation = ?, Concerns = ?, " \
                 "SCG = ?, DistributionStatement = ?, Tags = ?, Fields = ?, DataSetName = ?, OwnerPhone = ?,                 " \
                 "OwnerEmail = ?, CodeLibrary = ? WHERE MetadataID = " + id + " ;"
    cursor.execute(sql_update, params).commit()


# insert_FieldNames( list[string]| params)
# inserts the field name where the id equals the field ID and inserts the params
# params = (DataSet it belongs to, the field name, Description of the field, the tags associated with it)
def insert_FieldNames(params):
    sql_insert = "INSERT INTO FieldNames (DataSet, FieldName, Description, Units, Tags) VALUES (?,?,?,?,?);"

    cursor.execute(sql_insert, params).commit()

    sql_id = "SELECT ID FROM FieldNames WHERE DataSet ='" + flask.g[0] + "' AND FieldName ='" + params[1] + "';"

    pat = re.compile(r"""\d""")

    field_id = 'F'
    for ints in pat.findall(str(cursor.execute(sql_id).fetchone())):
        field_id += ints

    if params[4] != '':
        check_tags_delete_missing(params[4], 'FieldNames', 'ID', field_id)
        tags = params[4].split(';')
        for tag in tags:
            insert_tag(tag, field_id)
            more_tags = tag.split(' ')
            for tag_from_space in more_tags:
                if tag_from_space != '':
                    insert_tag(tag_from_space, field_id)
    return field_id


# update_FieldNames( list[string]| params, string| id)
# updates the field name where the id equals the field ID and updates the params
# params = (DataSet it belongs to, the field name, Description of the field, the tags associated with it)
def update_FieldNames(params, id):
    sql_update = "UPDATE FieldNames SET DataSet = ?, FieldName = ?, Description = ?, Units = ?, Tags = ? WHERE ID =" + id[
                                                                                                                       1:] + ";"
    cursor.execute(sql_update, params).commit()

    pat = re.compile(r"""\d""")
    field_id = 'F'
    for ints in pat.findall(id):
        field_id += ints

    if params[4] != '':
        check_tags_delete_missing(params[4], 'FieldNames', 'ID', field_id)
        tags = params[4].split(';')
        for tag in tags:
            insert_tag(tag, field_id)
            more_tags = tag.split(' ')
            for tag_from_space in more_tags:
                if tag_from_space != '':
                    insert_tag(tag_from_space, field_id)


# insert_tag( string| tag, string| data_key)
# inserts tag if it doesn't exists or inserts the key for the dataset or field name if tag exists
def insert_tag(tag, data_key):
    if tag != '':
        tag = clean_field_name(tag)
        sql_check = "SELECT * FROM Tags WHERE Word='" + tag + "';"
        check = cursor.execute(sql_check, params=None).fetchone()
        if check is None:
            sql_insert = "INSERT INTO Tags(Word, FieldsDataSets) VALUES(?, ?)"
            cursor.execute(sql_insert, params=[tag, data_key]).commit()
        else:
            tag_data_keys = check[2].split(';')
            new_data_keys = ''
            if not in_data_keys(data_key, tag_data_keys):
                tag_data_keys += [data_key]
                tag_data_keys.sort()
                for values in tag_data_keys:
                    new_data_keys += (values + ";")
                sql_update = "UPDATE Tags SET FieldsDataSets = ? WHERE Word = ?;"
                cursor.execute(sql_update, params=[new_data_keys[:-1], tag]).commit()


# delete_tag( string| tag, string| id)
# when a tag is removed from the text area this function will determine which tag and from which ID it is being removed
# from. It will then remove that ID from the tag and if there are no more IDs in the tag it will remove the tag
# from the database
def delete_tag(tag, id):
    sql_select = "SELECT FieldsDataSets FROM Tags WHERE Word = '" + tag + "';"
    fields_datasets = cursor.execute(sql_select).fetchone()
    new_string = ''
    if fields_datasets is None:
        return
    else:
        fields_datasets = fields_datasets[0]
        for ids in fields_datasets.split(';'):
            if ids == id:
                ids = ''
            new_string += ids + ';'
        new_string = new_string[:-1]
        if new_string == '':
            sql_delete = "DELETE FROM Tags WHERE Word = '" + tag + "';"
            cursor.execute(sql_delete)
        else:
            sql_update = "UPDATE Tags SET FieldsDataSets = ? WHERE Word = '" + tag + "';"
            cursor.execute(sql_update, params=[new_string])


# id in format (D342) or (F343)
def check_tags_delete_missing(new_tag_string, table, id_column, id):
    sql_select = "SELECT Tags FROM " + table + " WHERE " + id_column + " = " + id[1:] + ";"
    old_string = cursor.execute(sql_select).fetchone()[0]

    if new_tag_string == old_string:
        return
    else:
        new_string = new_tag_string.split(';')
        for tag in old_string.split(';'):
            if tag not in new_string:
                delete_tag(tag, id)
            for white_split_tag in tag.split(' '):
                if white_split_tag not in re.split(";|\s", new_tag_string):
                    delete_tag(white_split_tag, id)


# updates the string of field names in the metadata table
def update_metadata_fields_string():
    sql_select = "SELECT FieldName FROM FieldNames WHERE DataSet = '" + flask.g[0] + "';"
    field_list = cursor.execute(sql_select).fetchall()
    field_name_list = []
    new_string = ''
    for values in field_list:
        field_name_list += [values[0]]
    for field_name in field_name_list:
        field_name = clean_field_name(field_name)
        new_string += field_name + ';'
    sql_update = "UPDATE MetaData SET Fields = ? WHERE MetadataID = " + flask.g[0][1:] + ";"
    cursor.execute(sql_update, params=[new_string[:-1]])


# if organization does not exist in list than insert it into organizations table
def organizations_list_insert(organization):
    sql_select = "SELECT * FROM Organizations WHERE Organizations = '" + organization + "';"
    if cursor.execute(sql_select).fetchone() is None:
        sql_insert = "INSERT INTO Organizations (Organizations) VALUES (?);"
        cursor.execute(sql_insert, [organization])


# Ensures that the field names entered don't contain characters that would cause glitches in the code
def clean_field_name(field_name):
    list = field_name
    field_name = ''
    for character in list:
        if character == '\'':
            character = ''
        elif character == '\"':
            character = ''
        elif character == '\\':
            character = ''
        field_name += character
    return field_name


# checks the data keys in the tag to see if the key already exists in the list
def in_data_keys(data_key, tag_data_keys):
    for values in tag_data_keys:
        if data_key == values:
            return True
    return False

# If data is saved to access database, it will delete all data associated with the dataset id that is saved to flask.g
def cancel_form():
    sql_select = "SELECT Tags FROM Metadata WHERE MetadataID = " + flask.g[0][1:] + ";"
    tags = cursor.execute(sql_select).fetchone()[0]
    sql_select = "SELECT ID FROM FieldNames WHERE DataSet ='" + flask.g[0] + "';"
    two_d_list = cursor.execute(sql_select).fetchall()
    field_ids = []
    for elements in two_d_list:
        id = ('F' + str(elements[0]))
        field_ids += id
    for tag in tags.split(';'):
        sql_check = "SELECT * FROM Tags WHERE Word='" + tag + "';"
        check = cursor.execute(sql_check, params=None).fetchone()
        if check is not None:
            sql_select = "SELECT FieldsDataSets FROM Tags WHERE word='" + tag + "';"
            fields_and_datasets = cursor.execute(sql_select).fetchone()[0].split(';')
            for values in fields_and_datasets:
                if values == '' or values == flask.g[0]:
                    fields_and_datasets.remove(values)
                else:
                    for field_id in field_ids:
                        if values == field_id:
                            fields_and_datasets.remove(values)
    sql_delete = "DELETE FROM FieldNames WHERE DataSet = '" + flask.g[0] + "';"
    cursor.execute(sql_delete).commit()
    sql_delete = "DELETE FROM Metadata WHERE MetadataID = " + flask.g[0][1:] + ";"
    cursor.execute(sql_delete).commit()
    flask.g[0] = None

    return redirect(url_for("home_page"))


# takes in a list of params and creates a DataForm object that it puts the data into and sends back the object
def convert_to_data_form(params):
    Form = DataForm()

    Form.DataOwnerName = params[0]
    Form.DataOwnerOrganization = params[1]
    Form.AnalystName = params[2]
    Form.InterviewerName = params[3]
    Form.GuidanceInAcquiringData = params[4]
    Form.Format = params[5]
    Form.TotalSize = params[6]
    Form.ArchivingRules = params[10]
    Form.Frequency = params[7]
    Form.Source = params[8]
    Form.Version = params[9]
    Form.Header = params[11]
    Form.Tags = params[21]
    Form.ActionsTaken = params[15]
    Form.MetricsCollected = params[12]
    Form.MetricsToCollect = params[13]
    Form.DataDependencies = params[14]
    Form.VerificationOfData = params[17]
    Form.SecurityConcerns = params[18]
    Form.SCG = params[19]
    Form.DistributionStatement = params[20]
    Form.FieldNames = params[22]
    Form.DataSetName = params[23]
    Form.DataOwnerPhone = params[24]
    Form.DataOwnerEmail = params[25]
    Form.CodeLibrary = params[26]

    return Form


# parameters (string:(name of the table),string:(id number to look for),string:(the name of the id column) )
def in_table(table, data_column, data):
    sql_select = "SELECT * FROM " + table + " WHERE " + data_column + " = " + data + ";"
    if cursor.execute(sql_select).fetchone() != None:
        return True
    else:
        return False


# performs the search with the string in the parameters
# search order
# 1: Data set Name
# 2: Owner Name
# 3: Owner Organization
# 4: Field Name
# 5: Tags with multiple words in quotes
# 6: Tags with each word in the string
def search(search_string):
    search_list = []
    sql_select = "SELECT MetadataID FROM Metadata WHERE DatasetName = '" + search_string + "';"
    if cursor.execute(sql_select).fetchone() is not None:
        metadata_id = 'D' + str(cursor.execute(sql_select).fetchone()[0])
        add_hit(metadata_id, search_list)

    sql_select = "SELECT MetadataID FROM Metadata WHERE OwnerName = '" + search_string + "';"
    if cursor.execute(sql_select).fetchone() is not None:
        metadata_id = 'D' + str(cursor.execute(sql_select).fetchone()[0])
        add_hit(metadata_id, search_list)

    sql_select = "SELECT MetadataID FROM Metadata WHERE OwnerOrganization = '" + search_string + "';"
    if cursor.execute(sql_select).fetchone() is not None:
        metadata_id = 'D' + str(cursor.execute(sql_select).fetchone()[0])
        add_hit(metadata_id, search_list)

    sql_select = "SELECT ID FROM FieldNames WHERE FieldName = '" + search_string + "';"
    if cursor.execute(sql_select).fetchone() is not None:
        field_id = 'F' + str(cursor.execute(sql_select).fetchone()[0])
        add_hit(field_id, search_list)

    for words in re.findall(r'"([^"]*)"', search_string):
        sql_select = "SELECT FieldsDataSets FROM Tags WHERE Word = '" + words + "';"
        for id_numbers in cursor.execute(sql_select).fetchone()[0].split(';'):
            add_hit(id_numbers, search_list)

    for words in re.findall('\w+', search_string):
        sql_select = "SELECT FieldsDataSets FROM Tags WHERE Word = '" + words + "';"
        if cursor.execute(sql_select).fetchone() is not None:
            for id_numbers in cursor.execute(sql_select).fetchone()[0].split(';'):
                add_hit(id_numbers, search_list)
    return search_list


# called from search to add a hit or increase in integer value to the
# data set or field that has been found to have a match to the search_string
# all fields found will also give an additional hit to the data set it belongs to
def add_hit(id_number, search_list):
    search_hit = SearchHit()
    in_list = False
    for search_hits in search_list:
        if search_hits.IDNumber == id_number:
            search_hit = search_hits
            in_list = True

    if in_list:
        search_hit.Hit += 1
    else:
        search_hit.IDNumber = id_number
        search_hit.Hit += 1
        search_list.append(search_hit)

    if id_number[0] == 'F':
        sql_select = "SELECT DataSet FROM FieldNames WHERE ID = " + id_number[1:] + ";"
        dataset = cursor.execute(sql_select).fetchone()[0]

        add_hit(dataset, search_list)

    selection_sort_search_list(search_list)
    return search_list


# simple selection sort to place the object with the most hits in front
def selection_sort_search_list(search_list):
    for fill_slot in range(len(search_list) - 1, 0, -1):
        position_of_max = 0

        for index in range(1, fill_slot + 1):
            if search_list[index].Hit < search_list[position_of_max].Hit:
                position_of_max = index

        temp = search_list[fill_slot]
        search_list[fill_slot] = search_list[position_of_max]
        search_list[position_of_max] = temp


# takes the search_list[data set ID,Field ID] and turns the IDs into Metadata objects
# or Field objects so that the data can be displayed on the home page
def load_search_results(search_list):
    results = []
    for search_hit in search_list:
        if search_hit.IDNumber[0] == 'D':
            results.append(load_Metadata_searched(search_hit.IDNumber))
        else:
            results.append(load_Field_Data(search_hit.IDNumber))
    return results


# takes the field name ID number and creates a Field class object
# inputting the data from the database into the object and it gets
# added to the results list
def load_Field_Data(FieldID):
    sql_select = "SELECT * FROM FieldNames WHERE ID = " + FieldID[1:] + ";"
    field_data = cursor.execute(sql_select).fetchone()
    if field_data is not None:
        new_field = Field()
        new_field.fieldID = 'F' + str(field_data[0])
        new_field.dataset = field_data[1]
        new_field.name = field_data[2]
        new_field.description = field_data[3]
        new_field.units = field_data[4]
        new_field.tags = field_data[5]
        return new_field


if __name__ == "__main__":
    app.run()
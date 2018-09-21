from flask_wtf import form
from wtforms import StringField, IntegerField, TextAreaField, SubmitField, RadioField, SelectField, validators, ValidationError


class Field(form.FlaskForm):
    dataset = ''
    name = ''
    description = ''
    units = ''
    tags = ''

    collapseButtonTargetID = ''
    collapseButtonID = ''
    nameID = ''
    descriptionID = ''
    unitsID = ''
    tagsID = ''
    fieldID = ''


class DataForm(form.FlaskForm):
    DataSetName = ''
    DataSetID = ''
    DataOwnerName = ''
    DataOwnerOrganization = ''
    DataOwnerPhone = ''
    DataOwnerEmail = ''
    AnalystName = ''
    InterviewerName = ''
    GuidanceInAcquiringData = ''
    Format = ''
    TotalSize = ''
    ArchivingRules = ''
    Frequency = ''
    Source = ''
    Version = ''
    Header = ''
    Tags = ''
    ActionsTaken = ''
    MetricsCollected = ''
    MetricsToCollect = ''
    DataDependencies = ''
    VerificationOfData = ''
    SecurityConcerns = ''
    SCG = ''
    DistributionStatement = ''
    FieldNames = ''
    FieldIds = ''
    Created = ''
    LastUpdated = ''
    CodeLibrary = ''
    Image = ''
    multipleFields = []
    organizations = []

class SearchHit():
    IDNumber = ''
    MetadataID = ''
    Hit = 0

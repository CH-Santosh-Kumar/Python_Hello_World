from flask import Flask, request,render_template,redirect
from flask_bootstrap import Bootstrap
from twilio.base.exceptions import TwilioRestException
from twilio.twiml.voice_response import VoiceResponse
import requests
from twilio.rest import Client

# initialing app in Flask
app = Flask(__name__)

Bootstrap(app)
# Dictionaries to fetch employee name, Incident state and assignment group provided by status details module
emp_id = {
    '1422197': 'Travie',
    '103868': 'Shreyas'
}
inc_state = {'1': 'Active',
             '2': 'In progress',
             '3': 'On hold',
             '6': 'Resolved'}

Assignment_grp = {'d625dccec0a8016700a222a0f7900d06': 'Service Desk',
                  '': 'Data not available'
                  }

# URL's for service now Incident creation and fetching incident details with required parameters
url = 'https://dev66982.service-now.com/api/now/table/incident?sysparm_limit=10'


# User credentials for Service Now
user = 'admin'
pwd = 'Santosh@802'

# Set proper headers
headers = {"Content-Type": "application/xml", "Accept": "application/json"}


@app.route("/voice", methods=['GET', 'POST'])
def voice():
    """Respond to incoming phone calls with a menu of options"""
    # Start our TwiML response
    resp = VoiceResponse()

    # Start our <Gather> verb for welcoming customer at pepsico VIR.
    with resp.gather(action="/employee", input='speech', speechModel='numbers_and_commands', timeout='6', numDigits='1', finishOnKey='#', language='en-IN') as gather:
        gather.say('Welcome to automated help desk. Please provide you G P I D..')

    # If the user doesn't select an option, redirect them into a loop
    resp.redirect('/voice')
    return str(resp)


@app.route("/employee", methods=['GET', 'POST'])
def employee():
    """ Employee module helps gather user name and other
    respective details for effective greeting and further conversation.
    User is prompted with options to select from incident and status details. """
    value = ''
    global id
    resp = VoiceResponse()
    value = request.values['SpeechResult']
    getVals = list([val for val in value
                   if val.isnumeric()])
    value2 = ''.join(getVals)
    id = value2.replace('0','')
    print('id : {} and name : {}'.format(id, emp_id[id]))

    if id == '1422197':
        with resp.gather(action='/selection', input='speech dtmf', timeout='5', numDigits='1', finishOnKey='#',
                         language='en-IN') as gather:
            gather.say('Hello {}. To get details of existing issue please say Status. In case of new issue say Incident.'.format(emp_id[id]))

    resp.redirect('/employee')
    return str(resp)


@app.route("/selection", methods=['GET', 'POST'])
def selection():

    """
    This module will help user to redirect to incident flow if selected
    or provides incident status details depending on user selection.
    :return: response
    """
    global choice, body
    resp = VoiceResponse()
    choice = request.values['SpeechResult']
    # caller_number = request.values.get('From')
    # twilio_number = request.values.get('To')
    # print(choice + ", " + caller_number + ", " + twilio_number)

    if choice == 'incident' or choice == 'Incident':
        with resp.gather(action='/create_incident', input='speech dtmf', timeout='5', numDigits='1', finishOnKey='#',
                         language='en-IN') as gather:
            gather.say('Please provide short description for issue your are facing.')

        resp.redirect('/selection')

    elif choice == 'Status details' or choice == 'status' or choice == 'Status':

        global body

        url2 = 'https://dev66982.service-now.com/api/now/table/incident?sysparm_query=opened_by.name%3E%3D' \
               + emp_id[id] + '%5EGOTOactive%3E%3Dtrue' \
               '&sysparm_fields=number%2Cshort_description%2Cassignment_group%2Cstate&sysparm_limit=10'

        headers = {"Content-Type": "application/xml", "Accept": "application/json"}

        response = requests.get(url=url2, auth=(user, pwd), headers=headers)

        data = response.json()

        x = len(data['result'])
        body = []
        assignment = ''

        print("Below are the incidents raised by you. \n")

        resp.say('Please find status of incidents raised by you')

        for i in range(x):

            Numb = data['result'][i]['number']
            detail = data['result'][i]['short_description']
            x = data['result'][i]['assignment_group']

            if x != '':
                for value in x.values():
                    if value == 'd625dccec0a8016700a222a0f7900d06':
                        assignment = Assignment_grp['d625dccec0a8016700a222a0f7900d06']
            elif x == '':
                assignment = Assignment_grp['']

            if data['result'][i]['state'] == '6':
                continue
            state = data['result'][i]['state']

            resp.say('For incident number {}.'.format(Numb))
            resp.say('Short description is {}.'.format(str(detail)))
            resp.say('Incident is assigned to {}.'.format(assignment))
            resp.say('Currently incident is {}'.format(inc_state[state]))

            body.append(Numb + ' , ' + str(detail) + ' , ' + assignment + ' , ' + inc_state[state] + '\n')

        with resp.gather(action='/redirection', input='speech dtmf', timeout='5', numDigits='1', finishOnKey='#',
                         language='en-IN') as gather:
            gather.say('Is there anything else i can help you with ? Say yes to continue or no to close call.')

        print(body)

    return str(resp)


@app.route("/create_incident", methods=['GET', 'POST'])
def create_incident():
    """
    Customer will get redirect to this module once choose incident option.
    Incident will be raised on Service Now based on shared details.
    :return: response
    """
    global concern, incident_number
    resp = VoiceResponse()
    concern = request.values['SpeechResult']
    print(concern)

    resp.say('You said {}. We will raise an incident with service now with provided details'.format(concern))
    response = requests.post(url, auth=(user, pwd),
                             headers=headers,
                             data="<request><entry><short_description>{}</short_description>"
                                  "<assignment_group>Service Desk </assignment_group>"
                                  "<urgency>1</urgency><impact>2</impact></entry></request>".format(concern))

    data = response.json()
    incident_number = data['result']['number']

    resp.say('Incident number has been raised. \n'
             ' Please note the number {}'.format(incident_number))

    with resp.gather(action='/redirection', input='speech dtmf', timeout='5', numDigits='1', finishOnKey='#',
                     language='en-IN') as gather:
        gather.say('Is there anything else i can help you with ? Say yes to continue or no to close call.')

    resp.redirect('/voice')
    return str(resp)


@app.route("/redirection", methods=['GET', 'POST'])
def redirection():
    """
    This module will be called once user passes the incident creation or incident Status flow.
    Based on this flow call will be wither redirected to agent or will end with a thanking note.
    :return:response
    """
    global spoke
    resp = VoiceResponse()
    spoke = request.values['SpeechResult']
    #resp.say("Please stay on call we will be forwarding your call to one of our representative.")
    #resp.dial('+919892380045')

    if spoke == 'yes.' or spoke == 'Yes.' or spoke == 'yes' or spoke == 'Yes':
        resp.say("Please stay on call we will be forwarding your call to one of our representative.")
        resp.dial('+919892380045')

    elif spoke == 'no' or spoke == 'No' or spoke == 'no.' or spoke == 'No.':
        resp.say('Thank you for calling automated help desk.')

    return str(resp)

@app.route("/triggerResponse", methods=['GET', 'POST'])
def triggerResponse():

    if spoke == 'yes' or spoke =='Yes.' or spoke == 'Yes' or spoke == 'yes.':
        if choice == 'incident' or choice == 'Incident':
            return render_template("index.html", id=id, name=emp_id[id], choice='Creation of new incident', concern=concern,
                               incident_number=incident_number)
        elif choice == 'Status details' or choice == 'status' or choice == 'Status':
            return render_template("status.html", id=id, name=emp_id[id], choice='Status of Existing incident', body=body)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")

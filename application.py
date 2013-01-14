#!/usr/bin/env python

from flask import *
import boto
import urllib
import os

# The WSGI configuration on Elastic Beanstalk requires 
# the callable be named 'application' by default.
application = Flask(__name__)

# Setup the root route of the website, and render the 'index.html' template
@application.route("/")
def default():
	#display welcome page
	return render_template('index.html')

@application.route("/page2")
def page2():
	return render_template('page2.html')


@application.route("/makemoney")
def makemoney():
	''' This page has the button used to start the amazon payment process
	'''


	dollar_amount=1.00
        amazon_amount="USD %0.2f" % dollar_amount


        referenceID = 'MyTransactionId1234'
	# referenceID is just for your records. If you want to
	# customize the experience by gathering some information
	# before the payment, and then using that information after
	# the payment, make a unique ID and store those details of
	# this transaction in the database.  When the payment is
	# confirmed by amazon, this referenceID will be part of that
	# message, so you can pull what you need from the database

        success_url = url_for('amazon_success_func', _external=True)
        fail_url = url_for('amazon_fail_func', _external=True)
        ipn_url = None

        immediateReturn="1"
        processImmediate="1"

        amazonform = getPayNowWidgetForm(
            amount=amazon_amount,
            description='Punchline to a joke',
            referenceId=referenceID,
            immediateReturn=immediateReturn,
            returnUrl=success_url,
            abandonUrl=fail_url,
            processImmediate=processImmediate,
            #ipnUrl=ipn_url,                                                                                                                                            
            collectShippingAddress=False,
	    use_sandbox=True,
            )

        return render_template('buynow.html',
                               dollar_amount=dollar_amount,
                               amazon_form=amazonform,
                               )



def getStringToSign(formHiddenInputs,
                     host,
                     path,
                     ):
    formHiddenInputNames = formHiddenInputs.keys()
    formHiddenInputNames.sort()

    header='POST\n%(host)s\n%(path)s\n' % dict(
        host=host,
        path=path,
        )
    safestr = lambda x: x is not None and str(x) or ''
    safequote = lambda x: urllib.quote(safestr(x), safe='~')

    fieldtext = "&".join(['%s=%s' % (key, safequote(formHiddenInputs[key])) for key in formHiddenInputNames])
    out = header+fieldtext
    return out




def getbotofps(use_sandbox=True):

    if use_sandbox:
        hostname = 'fps.sandbox.amazonaws.com'
    else:
        hostname =  "fps.amazonaws.com"

    try:
	    fpsconn = boto.connect_fps(debug=2,
				       host=hostname)
    except boto.exception.NoAuthHandlerFound, e:
	    return None
    return fpsconn




def getPayNowWidgetForm(amount, description, referenceId = None, immediateReturn = None, returnUrl = None, abandonUrl = None,
                        processImmediate = None, ipnUrl = None, collectShippingAddress = None, use_sandbox=True):
    """                                                                                                                                                                 
    Generate a signed HTML form for a Pay Now Widget using the inputs provided                                                                                          
    """



    fpsconn = getbotofps(use_sandbox)
    if not fpsconn:
	    return 'unable to connect to fps. probably need to set AWS_ACCESS_KEY_ID'


    aws_access_key_id = str(boto.config.get('Credentials', 'aws_access_key_id', os.environ['AWS_ACCESS_KEY_ID']))

    if not aws_access_key_id:
	    return 'boto keys not found. I need a ~/.boto file'

    formHiddenInputs = {'accessKey': aws_access_key_id, 'amount': amount, 'description': description}
    if referenceId is not None:
        formHiddenInputs['referenceId'] = referenceId
    if immediateReturn is not None:
        formHiddenInputs['immediateReturn'] = immediateReturn
    if returnUrl is not None:
        formHiddenInputs['returnUrl'] = returnUrl
    if abandonUrl is not None:
        formHiddenInputs['abandonUrl'] = abandonUrl
    if processImmediate is not None:
        formHiddenInputs['processImmediate'] = processImmediate
    if ipnUrl is not None:
        formHiddenInputs['ipnUrl'] = ipnUrl


    formHiddenInputs['cobrandingStyle'] = 'logo'

    hostname = use_sandbox and 'payments-sandbox' or 'payments'
    endpoint =  "authorize.%s.amazon.com" % hostname
    path = '/pba/paypipeline'
    actionurl =  "https://%s%s" % (endpoint, path)

    formHiddenInputs.update({
            'SignatureMethod':  'HmacSHA256',
            'SignatureVersion': '2',
            })


    stringToSign = getStringToSign(formHiddenInputs, endpoint, path)
    #print stringToSign

    formHiddenInputs['signature'] = fpsconn._auth_handler.sign_string(stringToSign)

    form =  '<form action="%s" method="POST">\n' % actionurl
    form += '<input type="image" src="https://authorize.payments.amazon.com/pba/images/payNowButton.png" border="0" >\n'
    formHiddenInputNames = formHiddenInputs.keys()
    parameters = "".join(['<input type="hidden" name="' + key + '" value="' + formHiddenInputs[key] + '">\n' for key in formHiddenInputNames])
    form = form + parameters + '</form>'

    #print form
    return form

@application.route("/success")
def amazon_success_func():
	''' 
	This page is called when the payment is accepted. You can
	verify the signature of that message, but we don't yet do
	that. Instead we just show what the user paid for
	'''
	return render_template('success.html')

@application.route("/failure")
def amazon_fail_func():
	'''
	This page is shown if the payment failed
	'''
	
	return render_template('failure.html')



if __name__ == '__main__':
	application.debug = True
	application.run(host='0.0.0.0')

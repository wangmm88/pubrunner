import pubrunner
import os
import shutil
import requests
import json

def pushToFTP(outputDir,toolSettings,globalSettings):
	FTP_ADDRESS = globalSettings["upload"]["ftp"]["url"]
	FTP_USERNAME = globalSettings["upload"]["ftp"]["username"]
	FTP_PASSWORD = globalSettings["upload"]["ftp"]["password"]
	# N.B. This doesn't recursively copy files

	# Push output folder contents
	# 1. Set up FTP
	ftpc = pubrunner.FTPClient(FTP_ADDRESS, FTP_USERNAME, FTP_PASSWORD)
	# 2. Go the the right directory, or create it
	ftpc.cdTree(toolSettings["name"]+"/"+str(toolSettings["version"])+"/")
	# 3. Upload all files
	for f in os.listdir(outputDir):
		fPath = os.path.join(outputDir, f)
		if os.path.isfile(fPath):
			ftpc.upload(outputDir, f)
	# 4. Close session
	ftpc.quit()

	# Delete that content locally
	for f in os.listdir(outputDir):
		fPath = os.path.join(outputDir, f)
		try:
			if os.path.isfile(fPath):
				os.unlink(fPath)
		except Exception as e:
			print(e)

def pushToLocalDirectory(outputDir,toolSettings,globalSettings):
	LOCAL_DIRECTORY = globalSettings["upload"]["local-directory"]["path"]

	destDir = os.path.join(LOCAL_DIRECTORY,toolSettings["name"],str(toolSettings["version"]))
	if not os.path.isdir(destDir):
		os.makedirs(destDir)

	# N.B. This doesn't recursively copy files
	for f in os.listdir(outputDir):
		src = os.path.join(outputDir, f)
		dst = os.path.join(destDir, f)
		if os.path.isfile(src):
			shutil.copyfile(src,dst)

def pushToZenodo(outputDir,toolSettings,globalSettings):
	#if globalSettings["upload"]["zenodo"]["sandbox"] == True:
	ZENODO_URL = 'https://sandbox.zenodo.org'
	#else:
	#	ZENODO_URL = 'https://zenodo.org'
	ZENODO_AUTHOR = 'TODO'
	ZENODO_AUTHOR_AFFILIATION = 'TODO'

	ACCESS_TOKEN = globalSettings["upload"]["zenodo"]["token"]
	
	print("  Creating new Zenodo submission")
	headers = {"Content-Type": "application/json"}
	r = requests.post(ZENODO_URL + '/api/deposit/depositions',
					params={'access_token': ACCESS_TOKEN}, json={},
					headers=headers)

	assert r.status_code == 201, "Unable to create Zenodo submission (error: %d) " % r.status_code

	bucket_url = r.json()['links']['bucket']
	deposition_id = r.json()['id']
	doi = r.json()["metadata"]["prereserve_doi"]["doi"]
	doiURL = "https://doi.org/" + doi
	print("  Got provisional DOI: %s" % doiURL)

	print("  Adding files to Zenodo submission")
	for f in os.listdir(outputDir):
		src = os.path.join(outputDir, f)
		if os.path.isfile(src):
			r = requests.put('%s/%s' % (bucket_url,f),
							data=open(src, 'rb'),
							headers={"Accept":"application/json",
							"Authorization":"Bearer %s" % ACCESS_TOKEN,
							"Content-Type":"application/octet-stream"})


			assert r.status_code == 200, "Unable to add file to Zenodo submission (error: %d) " % r.status_code

	print("  Adding metadata to Zenodo submission")
	data = {
			'metadata': {
					'title': toolSettings['name'],
					'upload_type': 'dataset',
					'description':	'Results from tool executed using PubRunner on MEDLINE corpus.',
					'creators': [{'name': ZENODO_AUTHOR,
							'affiliation': ZENODO_AUTHOR_AFFILIATION}]
			}
	}

	r = requests.put(ZENODO_URL + '/api/deposit/depositions/%s' % deposition_id,
					params={'access_token': ACCESS_TOKEN}, data=json.dumps(data),
					headers=headers)

	assert r.status_code == 200, "Unable to metadata to Zenodo submission (error: %d) " % r.status_code

	#print("  Publishing Zenodo submission")
	#r = requests.post(ZENODO_URL + '/api/deposit/depositions/%s/actions/publish' % deposition_id,
	#				 params={'access_token': ACCESS_TOKEN} )
	#assert r.status_code == 202, "Unable to publish to Zenodo submission (error: %d) " % r.status_code

	#return doiURL


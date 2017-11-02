
from pubrunner.command_line import *
from pubrunner.upload import *
from pubrunner.getresource import *
from pubrunner.pubrun import pubrun,cleanWorkingDirectory
from pubrunner.convert import *
from pubrunner.pubmed_hash import pubmed_hash
from pubrunner.gather_pmids import gatherPMIDs

def calcSHA256(filename):
	return hashlib.sha256(open(filename, 'rb').read()).hexdigest()

def calcSHA256forDir(directory):
	sha256s = {}
	for filename in os.listdir(directory):
		sha256 = calcSHA256(os.path.join(directory,filename))
		sha256s[filename] = sha256
	return sha256s

def loadYAML(yamlFilename):
	yamlData = None
	with open(yamlFilename,'r') as f:
		try:
			yamlData = yaml.load(f)
		except yaml.YAMLError as exc:
			print(exc)
			raise
	return yamlData

def promptuser(prompt='> ', accepted=None):
	while True:
		print(prompt,end='')
		sys.stdout.flush()
		userinput = sys.stdin.readline().strip()
		if accepted is None or userinput in accepted:
			break
		else:
		 	print("Input not allowed. Must be one of %s" % str(accepted))
	return userinput

def setupDefaultGlobalSettingsFile(globalSettingsPath):
	defaultPath = os.path.join(pubrunner.__path__[0],'pubrunner.settings.default.yml')
	with codecs.open(defaultPath,'r','utf-8') as f:
		defaultSettings = f.read()

	print("No global settings file (%s) was found. Do you want to install the default one (below)?\n" % globalSettingsPath)
	print(defaultSettings)

	userinput = promptuser(prompt='(Y/N): ',accepted=['Y','N','y','n'])
	if userinput.lower() == 'y':
		assert os.path.isfile(defaultPath), "Unable to find default settings file"
		shutil.copy(defaultPath,globalSettingsPath)

		print("Default settings installed. Do you want to continue with this run?")
		userinput = promptuser(prompt='(Y/N): ',accepted=['Y','N','y','n'])
		if userinput.lower() == 'n':
			print("Exiting...")
			sys.exit(0)
		
def findGlobalSettingsFile():
	homeDirectory = os.path.expanduser("~")
	globalSettingsPath = os.path.join(homeDirectory,'.pubrunner.settings.yml')
	if not os.path.isfile(globalSettingsPath):
		setupDefaultGlobalSettingsFile(globalSettingsPath)
	assert os.path.isfile(globalSettingsPath), "Unable to find ~/.pubrunner.settings.yml file."
	return globalSettingsPath

globalSettings = None
def getGlobalSettings():
	global globalSettings
	if globalSettings is None:
		settingsYamlFile = findGlobalSettingsFile()
		globalSettings = loadYAML(settingsYamlFile)

	return globalSettings

def launchSnakemake(snakeFilePath,useCluster=True,parameters={}):
	globalSettings = pubrunner.getGlobalSettings()
	
	clusterFlags = ""
	if useCluster and "cluster" in globalSettings:
		clusterSettings = globalSettings["cluster"]
		jobs = 1
		if "jobs" in globalSettings["cluster"]:
			jobs = int(globalSettings["cluster"]["jobs"])
		clusterFlags = "--jobs %d --latency-wait 60" % jobs

		if "drmaa" in clusterSettings and clusterSettings["drmaa"] == True:
			clusterFlags += ' --drmaa'
		elif "options" in clusterSettings:
			clusterFlags = "--cluster '%s'" % clusterSettings["options"]
		else:
			raise RuntimeError("Cluster must either have drmaa = true or provide options (e.g. using qsub)")

	makecommand = "snakemake %s -s %s" % (clusterFlags,snakeFilePath)

	env = os.environ.copy()
	env.update(parameters)

	retval = subprocess.call(shlex.split(makecommand),env=env)
	if retval != 0:
		raise RuntimeError("Snake make call FAILED (file:%s)" % snakeFilePath)

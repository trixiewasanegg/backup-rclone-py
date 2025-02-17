import json
import logging
import subprocess
import re
import sys

if len(sys.argv) == 2:
	flag = sys.argv[1]
	match flag:
		case "-d":
			logging.basicConfig(level=logging.DEBUG)
		case "-i":
			logging.basicConfig(level=logging.INFO)
		case "-w":
			logging.basicConfig(level=logging.WARNING)
	logging.debug(f"Set log level to {logging.root.level} from flag")
else:
	logging.basicConfig(level=logging.INFO)
	logging.debug(f"Set to default info logging level")

logging.basicConfig(format="{levelname} - {asctime} : {message}", style="{", datefmt="%Y-%m-%d %H:%M")

# Reads the JSON config file
logging.info("Reading JSON file...")
with open("backupconf.json",mode="r") as jsonFile:
	conf = dict(json.loads(jsonFile.read()))
logging.info("Done")

# Checks remotes
logging.info("Checking remotes...")

# Pulls current rclone config into dictionary
cmd = ["rclone", "config", "dump"]
currentConf = subprocess.run(cmd, capture_output = True, text = True)
currentConf = dict(json.loads(currentConf.stdout))

# Checks remotes against current config
for remote in conf["remotes"]:
	logging.debug(f"Matching config to {remote}")
	confDict = conf["remotes"][remote]
	# Exception catcher incase remote not in config
	try:
		currentConfDict = currentConf[remote]
	except:
		currentConfDict = ""
	
	# checks if the dictionaries match, creates if not
	if confDict != currentConfDict:
		logging.debug(f"Creating new remote...")

		# Get name & type, remove type from dictionary
		remote_name = remote
		remote_type = confDict["type"]
		confDict.pop("type")

		cmd = ["rclone", "config", "create", remote_name, remote_type]
		# Pulls key/value pairs for other arguments
		try:
			for k, v in confDict.items():
				cmd.append(k)
				cmd.append(v)
		except:
			cmd = cmd

		# Formats into command then executes
		logging.debug(subprocess.run(cmd, capture_output=True, text=True).stdout)
		logging.debug("Remote created")
	else:
		logging.debug(f"{remote} already exists and matches config")
logging.info("Done")

# Tasks as defined by json file
logging.info("Starting tasks")

# Gets task count for logging
taskCnt = len(conf["tasks"])
n = 0
for tasks in conf["tasks"]:
	n = n+1
	name = tasks['name']
	logging.info(f"Starting task {n} of {taskCnt}: {name}")
	
	# Adds verbosity to arguments for debug logging
	args = tasks["args"]
	if not "-v" in args or "-vv" in args:
		args.append("-v")

	cmd = ["rclone", tasks["task"], tasks["src"], tasks["dest"]] + args
	cmd[:] = (val for val in cmd if val != "")

	# runs process, pulling stdout into a pipe for realtime logging
	process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

	# Realtime logging
	for line in process.stdout:
		# Changes bytes into string
		line = line.decode("utf-8").replace("\n","")

		level = "info"

		#Regex to check if it begins with the datetime, reformats accordingly
		if re.search("[0-9]{4}\\/[0-9]{2}\\/[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}",line) != None:
			level = "debug"
			line = "".join(line[19:].split(':')[1:]).strip()
			if line != "There was nothing to transfer" and line != "":
				line = f"Modified     : {line}"
		
		# Checks if beginning starts with the ending log lines
		elif (line[0:11] == "Transferred") or (line[0:6] == "Checks") or (line[0:12] == "Elapsed time") or (line[0:6] == "Deleted"):
			line = line.split(":")
			line = line[0] + (" "*(14-len(line[0])))+ ": " + line[1].strip()

		# If the line is not blank, log it as debug
		if line != "":
			line = f"Task {n} ({name}): {line}"
			match level:
				case "debug":
					logging.debug(line)
				case "info":
					logging.info(line)

	logging.info(f"Completed task {n}: {name}")
logging.info("Tasks complete")
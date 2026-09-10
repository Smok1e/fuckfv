import json, logging, re, requests, traceback
from lks_api import LksApi
import datetime

#========================================

class SignUpError(RuntimeError): ...

#========================================

def send_telegram_message(config: dict, text: str, parse_mode = None):
	data = {
		"chat_id": config["chat_id"],
		"text": text
	}

	if parse_mode is not None:
		data["parse_mode"] = parse_mode

	response = requests.post(
		f"{config["base_url"]}/bot{config["token"]}/sendMessage",
		data = data,
		proxies = {
			"http": config["proxy"],
			"https": config["proxy"]
		}
	)

	data = response.json()
	if not data["ok"]:
		raise RuntimeError(f"Request to telegram api failed: {data["description"]}")

def sign_up_best_group(config):
	api = LksApi(config["api"])

	response = api.get("fv/bc902d56-23bc-11ee-8128-0242ac110002/tails")
	data = response.json()

	pattern = re.compile(config["tails"]["pattern"], re.UNICODE | re.DOTALL)
	groups = list(
		filter(
			lambda group: pattern.match(group["comment"]) is not None,
			data["groups"]
		)
	)

	if len(groups) < 1:
		raise SignUpError("No matching groups found")

	groups = list(
		filter(
			lambda group: group["busyDisplay"] is None,
			groups
		)
	)

	if len(groups) < 1:
		raise SignUpError("All matching groups are occupied")

	for group in groups:
		group["datetime"] = datetime.datetime.combine(
			datetime.date.fromisoformat(group["date"]),
			datetime.time.fromisoformat(group["timeStart"])
		)

	group = sorted(groups, key = lambda group: group["datetime"], reverse = True)[0]

	response = api.post(f"fv/bc902d56-23bc-11ee-8128-0242ac110002/groups/{group["id"]}/tail")
	data = response.json()

	if data["status"] != 200:
		raise SignUpError(f"Response status is {data["status"]}: {json.dumps(data)}")

	return group, data["message"]
		# (
		# f"'{group["comment"]}' ({group["id"]}), {group["date"]} {group["timeStart"]}; {group["occupied"]}/{group["capacity"]} occupied",
		# data["message"])

def main():
	with open("config.json", "rb") as file:
		config = json.load(file)

	try:
		group, message = sign_up_best_group(config)
		logging.info(f"Success")
		send_telegram_message(
			config["telegram"], (
				f"<b>{message}</b>\n"
				f"\n"
				f"<b>{group["comment"]}</b>, "
				f"<tg-time unix=\"{group["datetime"].timestamp()}\">{group["datetime"].strftime("%d.%m.%Y %H:%M")}</tg-time>, "
				f"<b>{group["occupied"]}/{group["capacity"]}</b> occupied."
			),
			parse_mode = "HTML"
		)

	except SignUpError as err:
		logging.error(f"Sign up failed: {err}")
		send_telegram_message(config["telegram"], f"Sign up failed: {err}")

	except RuntimeError as err:
		traceback.print_exc()
		send_telegram_message(config["telegram"], f"Unexpected error: {err}; see logs")

#========================================

if __name__ == "__main__":
	logging.basicConfig(level = logging.INFO)
	main()

#========================================
import requests, logging, json
from http import HTTPStatus
from bs4 import BeautifulSoup

class LksApi(requests.Session):
	def __init__(self, config):
		super().__init__()
		self.config = config

		try:
			self._load_cookies()

		except FileNotFoundError:
			logging.info("Cookies file not found, authorizing")
			self._authorize()

	def _authorize(self):
		self.cookies.clear()

		response = super().request(
			"GET",
			self.config["login_url"],
			params = {
				"back": self.config["login_back_url"],
				"profile_any": "true"
			}
		)

		soup = BeautifulSoup(response.content, "html.parser")
		action = str(soup.form["action"])

		super().request(
			"POST",
			action,
			data = {
				"username": self.config["username"],
				"password": self.config["password"],
				"credentialId": ""
			}
		)

		logging.info("Authorization successful")
		self._save_cookies()

	def _save_cookies(self):
		with open(self.config["cookies_path"], "w") as file:
			json.dump(requests.utils.dict_from_cookiejar(self.cookies), file, indent = 4)

		logging.info("Cookies saved")

	def _load_cookies(self):
		with open(self.config["cookies_path"], "r") as file:
			self.cookies.update(requests.utils.cookiejar_from_dict(json.load(file)))

		logging.info("Cookies loaded")

	def request(self, method, url, *args, **kwargs):
		url = f"{self.config["base_url"]}/{url}"

		response = super().request(method, url, *args, **kwargs)

		if response.status_code == HTTPStatus.UNAUTHORIZED:
			logging.info("Authorization rotted, authorizing again...")
			self._authorize()

			response = super().request(method, url, *args, **kwargs)

		return response
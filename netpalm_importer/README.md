# Netpalm -> Netbox Importer

Quick and dirty node script with a lot hardcoded still at the moment.

However, it works to grab interfaces off your devices and spits out a csv ready to import into netbox.

### Getting Started

1. Customize your netpalm `netmiko_retrieve_data` service call arguments.
2. Run `node index.js retrieve`
3. Copy the resulting `taskId`
4. Run `node index.js task [taskId]` replace `[taskId]` with the ID you just copied
5. While its still running it will return "Running", however once its completed it will return **"Interfaces dumped!"**

You will then have an interfaces.csv file in your project root with the results based upon the format in the `getTask` function

### To Do

- Definitely need to make much more of this dynamic.
	- i.e. Ability to define API Key, Username, Password, etc. in `.env` file for example
	- Define output format
	- Define output fields which will be the same for all interfaces, i.e. `device`

### Contributing

Feel free to open a PR

#### License

MIT

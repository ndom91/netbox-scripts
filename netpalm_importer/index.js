const fetch = require("isomorphic-unfetch")
const createCsvWriter = require("csv-writer").createObjectCsvWriter

const commands = ["retrieve", "task", "help"]
const args = process.argv

const usage = function () {
  const usageText = `
  netbox netpalm node cli

  usage:
    nbnp <command>

    commands can be:

    retrieve:  used to scan convertors in your inventory.json.
    task:      used to query secondary Ids found via scan.
    help:      used to print the usage guide.
  `
  console.log(usageText)
  return
}

if (commands.indexOf(args[2]) == -1) {
  console.error("invalid command passed")
  usage()
}

const retrieveData = async () => {
  const raw = JSON.stringify({
    operation: "retrieve",
    args: {
      hosts: ["192.168.11.250"],
      username: "",
      password: "",
      driver: "cisco_ios",
      command: "show int",
    },
    queue_strategy: "fifo",
  })

  const requestOptions = {
    method: "POST",
    headers: {
      "x-api-key": "2a84465a-cf38-46b2-9d86-b84Q7d57f288",
      "Content-Type": "application/json",
    },
    body: raw,
    redirect: "follow",
  }

  const resp = await fetch(
    "http://127.0.0.1:9000/service/netmiko_retrieve_data",
    requestOptions
  )
  const data = await resp.json()
  console.log(data)
}

const getTask = async taskId => {
  const requestOptions = {
    method: "GET",
    headers: {
      "x-api-key": "2a84465a-cf38-46b2-9d86-b84Q7d57f288",
      "Content-Type": "application/json",
    },
    redirect: "follow",
  }

  const resp = await fetch(
    `http://127.0.0.1:9000/task/${taskId}`,
    requestOptions
  )
  const status = await resp.json()
  if (status.data.task_status !== "finished") {
    console.log(status)
  } else {
    const interfaces =
      status.data.task_result[0].data.data.task_result["show int"]
    const outInterfaces = []
    const csvWriter = createCsvWriter({
      path: "interfaces.csv",
      header: [
        { id: "device", title: "device" },
        { id: "name", title: "name" },
        { id: "type", title: "type" },
        { id: "enabled", title: "enabled" },
        { id: "mac_address", title: "mac_address" },
        { id: "mtu", title: "mtu" },
        { id: "description", title: "description" },
        { id: "mode", title: "mode" },
      ],
    })
    interfaces.forEach(int => {
      outInterfaces.push({
        device: "Cisco Switch 1",
        name: int.interface,
        type: "1000BASE-T (1GE)",
        enabled: int.link_status === "up",
        mac_address: int.address,
        mtu: int.mtu,
        description: int.description,
        mode: "Tagged",
      })
    })
    csvWriter
      .writeRecords(outInterfaces)
      .then(() => console.log("Interfaces written!"))
  }
}

switch (args[2]) {
  case "task":
    const taskId = args[3]
    getTask(taskId)
    break
  case "retrieve":
    retrieveData()
    break
  case "help":
    usage()
    break
  default:
    console.error("invalid command passed")
    usage()
}

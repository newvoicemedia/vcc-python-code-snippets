## wfm-agent-state sample

The sample application demonstrate best practice approaches for using the `/wfm/agent-state` endpoint of the insights stats api.

Please consult the insights stats api documentation for more information.

### Setup
These sample applications are written in Python and use [Pipenv](https://realpython.com/pipenv-guide/) to manage dependencies. Please ensure Python 3.8+ and Pipenv are installed on your system before running these sample applications.

In the sample application directory, execute:
```
pipenv install
```
to install the required dependencies.

### Running the bulk_load sample
The bulk load sample is designed to be run once per hour. It fetches the last complete hours worth of data from the API and saves it locally into a SQLite database file (wfm_agent_state.db). The bulk load sample demonstrates a simpler integration which loads steady state data in fewer API calls, but necessarily involves latency of at least one hour.

To run the bulk load example, execute:
```
pipenv shell
python bulk_load.py [-u <base-url>] [-t <bearer-token>] [-p <page-size>]
```

The default base-url is 'https://nam.api.newvoicemedia.com'
The bearer-token parameter is required. Please consult the Vonage API documentation for instructions on how to generate a bearer token.
The default page size is 5000

If you do not specify a bearer token on the command line, you will be prompted to enter one.

### Running the real_time sample
The real time sample demonstrates a continuously running integration which polls for updated data every 15 seconds. It is a slightly more complicated sample, and involves more API calls because it will typically receive the same logical records in varying degrees of completeness until they are finalized. This sample is suitable when it is necessary to minimize latency. As with the previous sample, data will be saved into a local SQLite database file (wfm_agent_state.db). Additionally a .offset file will be created to keep track of where the sample application has queried up to. This is used when the sample application is restarted so that it can pick up where it left off.

To run the real time example, execute:
```
pipenv shell
python real_time.py [-u <base-url>] [-t <bearer-token>] [-p <page-size>]
```

The default base-url is 'https://nam.api.newvoicemedia.com'
The bearer-token parameter is required. Please consult the Vonage API documentation for instructions on how to generate a bearer token.
The default page size is 100

If you do not specify a bearer token on the command line, you will be prompted to enter one.

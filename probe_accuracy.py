# Create a Python environment for this script.  Use ssh to log in to the pi, and run the following:
#
#     sudo apt install python3-venv
#     python3 -m venv /home/pi/plotly-env
#     /home/pi/plotly-env/bin/pip install -U plotly
#     mkdir /home/pi/probe_accuracy
#
# Download probe_accuracy.py and copy it to the pi into /home/pi/probe_accuracy/ .
#
# To collect data, ssh into the pi and run the below command before doing TEST_PROBE_ACCURACY:
#
#     /home/pi/plotly-env/bin/python3 /home/pi/probe_accuracy/probe_accuracy.py
#
# Leave that ssh session/window open for the duration of the test.  After the test completes, the
# chart should be in /tmp/probe_accuracy.html. Copy that file from the pi to your local machine
# and open it.
#
# If you specify --plot-only the script will not collect data from Klipper, but instead plot an
# existing JSON data file pointed to by --data-file.

import argparse
import json
import re
import socket
import time
from statistics import pstdev

import plotly.graph_objects as pgo
from plotly.subplots import make_subplots

parser = argparse.ArgumentParser()
parser.add_argument('--klippy-uds', default='/tmp/klippy_uds')
parser.add_argument('--data-file', default='/tmp/probe_accuracy.json')
parser.add_argument('--chart-file', default='/tmp/probe_accuracy.html')
parser.add_argument('--plot-only', action='store_true',
                    help='plot existing file specified by --data-file instead of collecting data from Klipper')

KLIPPY_KEY = 31415926
GCODE_SUBSCRIBE = {
    'params': {'response_template': {'key': KLIPPY_KEY}},
    'id': 42,
    'method': 'gcode/subscribe_output'
}
TEST_END_MARKER = 'TEST_PROBE_ACCURACY: DONE'

BED_THERMISTOR_ID = 'B'
EXTRUDER_THERMISTOR_ID = 'T0'
START_RE = re.compile(r'// TEST_PROBE_ACCURACY: START')
# B:40.1 /40.0 PI:45.3 /0.0 T0:59.8 /60.0
TEMP_RE = re.compile(r'(?P<id>[\w-]+):(?P<temp>[0-9.]+)\s*/(?P<set>[0-9.]+)')
# // probe at 175.000,175.000 is z=2.027500
PROBE_RE = re.compile(r'^// probe at [0-9.,]+ is z=(?P<z>[0-9.-]+)')


def get_klippy_output(klippy_uds: str):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(klippy_uds)

    try:
        sock.sendall(json.dumps(GCODE_SUBSCRIBE, separators=(',', ':')).encode() + b'\x03')

        remainder = b''
        while True:
            data = sock.recv(4096)
            parts = data.split(b'\x03')
            parts[0] = remainder + parts[0]
            remainder = parts.pop()
            for part in parts:
                line = part.decode()
                if str(KLIPPY_KEY) not in line:
                    continue
                if TEST_END_MARKER in line:
                    return
                yield line
    finally:
        sock.close()


def parse_response(response: str) -> dict:
    ts = time.time()

    # Parse Z height output.
    m = PROBE_RE.match(response)
    if m:
        d = {
            'ts': ts,
            'z': float(m.group('z'))
        }
        return d

    # Parse thermistor output.
    tmatches = list(TEMP_RE.finditer(response))
    if tmatches:
        d = {'ts': ts}
        for m in tmatches:
            if m.group('id') == BED_THERMISTOR_ID:
                d['btemp'] = float(m.group('temp'))
                d['bset'] = float(m.group('set'))
            elif m.group('id') == EXTRUDER_THERMISTOR_ID:
                d['etemp'] = float(m.group('temp'))
                d['eset'] = float(m.group('set'))
            else:
                ad = {
                    'id': m.group('id'),
                    'temp': float(m.group('temp')),
                    'set': float(m.group('set'))
                }
                try:
                    d['atherms'].append(ad)
                except KeyError:
                    d['atherms'] = [ad]
        return d


def get_data(klippy_uds: str, data_file: str) -> list:
    data = []
    with open(data_file, 'w') as f:
        for line in get_klippy_output(klippy_uds):
            klippy_response = json.loads(line)
            response = klippy_response['params']['response']

            d = parse_response(response)
            if d:
                data.append(d)
                f.write(json.dumps(d, separators=(',', ':')) + '\n')
                f.flush()

    return data


def load_data(data_file: str) -> list:
    with open(data_file, 'r') as f:
        return [json.loads(line) for line in f]


def write_chart(data: list, output_file: str):
    min_ts = data[0]['ts']

    ztrace = pgo.Scatter(
        x=[x['ts'] - min_ts for x in data if 'z' in x],
        y=[x['z'] for x in data if 'z' in x],
        name='Z',
        mode='lines',
        line={'color': 'black'},
        yaxis='y2'
    )

    zstddevtrace = pgo.Scatter(
        x=[ts for i, ts in enumerate(ztrace.x) if i >= 4],
        y=[pstdev(ztrace.y[i-4:i+1]) * 1000 for i, ts in enumerate(ztrace.y) if i >= 4],
        name='Z stddev',
        mode='markers',
        line={'color': 'gray'},
        yaxis='y3'
    )

    btrace = pgo.Scatter(
        x=[x['ts'] - min_ts for x in data if 'btemp' in x],
        y=[x['btemp'] for x in data if 'btemp' in x],
        name='bed temperature',
        mode='lines',
        line={'color': 'blue'}
    )
    bstrace = pgo.Scatter(
        x=[x['ts'] - min_ts for x in data if 'bset' in x],
        y=[x['bset'] for x in data if 'bset' in x],
        showlegend=False,
        mode='none',
        fill='tozeroy',
        fillcolor='rgba(128,128,255,0.3)'
    )

    etrace = pgo.Scatter(
        x=[x['ts'] - min_ts for x in data if 'etemp' in x],
        y=[x['etemp'] for x in data if 'etemp' in x],
        name='extruder temperature',
        mode='lines',
        line={'color': 'red'}
    )
    estrace = pgo.Scatter(
        x=[x['ts'] - min_ts for x in data if 'eset' in x],
        y=[x['eset'] for x in data if 'eset' in x],
        showlegend=False,
        mode='none',
        fill='tozeroy',
        fillcolor='rgba(255,128,128,0.3)'
    )

    fig = pgo.Figure()
    fig.add_trace(ztrace)
    fig.add_trace(zstddevtrace)
    fig.add_trace(btrace)
    fig.add_trace(bstrace)
    fig.add_trace(etrace)
    fig.add_trace(estrace)

    thermistors_xy = {}
    for d in data:
        if not 'atherms' in d:
            continue

        ts = d['ts'] - min_ts
        for ad in d['atherms']:
            therm_id = ad['id']
            temp = ad['temp']
            try:
                thermistors_xy[therm_id]['x'].append(ts)
                thermistors_xy[therm_id]['y'].append(temp)
            except KeyError:
                thermistors_xy[therm_id] = {
                    'x': [ts],
                    'y': [temp]
                }

    for therm_id, xy in thermistors_xy.items():
        trace = pgo.Scatter(
            x=xy['x'],
            y=xy['y'],
            name=f'{therm_id} temperature',
            mode='lines'
        )
        fig.add_trace(trace)

    fig.update_layout(
        title=dict(
            text='Probe Accuracy'
        ),
        legend=dict(
            x=1.1
        ),
        xaxis=dict(
            title='seconds',
            domain=[0, 0.9]
        ),
        yaxis=dict(
            title='°C',
        ),
        yaxis2=dict(
            title='Z (mm)',
            anchor='x',
            overlaying='y',
            side='right',
            position=0.9
        ),
        yaxis3=dict(
            title='Z stddev (µm)',
            rangemode='tozero',
            anchor='free',
            overlaying='y',
            side='right',
            position=1.0
        ),
    )

    fig.write_html(output_file)


def main():
    args = parser.parse_args()

    if args.plot_only:
        data = load_data(args.data_file)
    else:
        print('Recording data, LEAVE THIS SESSION OPEN UNTIL THE SCRIPT SAYS "DONE"!')
        data = get_data(args.klippy_uds, args.data_file)

    write_chart(data, args.chart_file)
    print(f'DONE, chart is in {args.chart_file}, chart data in {args.data_file}')


if __name__ == '__main__':
    main()

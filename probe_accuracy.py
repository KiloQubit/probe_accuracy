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
#     while read -r line; do echo `/bin/date +%s`: "$line"; done < /tmp/printer > /tmp/probe_accuracy.txt
#
# Leave that ssh session/window open for the duration of the test.  After TEST_PROBE_ACCURACY completes,
# go back to the ssh session and hit Ctrl+C to stop the data collection.  Then run this script with
#
#     /home/pi/plotly-env/bin/python3 /home/pi/probe_accuracy/probe_accuracy.py
#
# Copy the output file /tmp/probe_accuracy.html from the pi to your local machine and open it.

import argparse
import re

import plotly.graph_objects as pgo
from plotly.subplots import make_subplots

parser = argparse.ArgumentParser()
parser.add_argument('--data-file', default='/tmp/probe_accuracy.txt')
parser.add_argument('--output-file', default='/tmp/probe_accuracy.html')

START_RE = re.compile(r'// TEST_PROBE_ACCURACY: START')
# 1609027993: B:40.1 /40.0 PI:45.3 /0.0 T0:59.8 /60.0
TEMP_RE = re.compile(r'^(?P<ts>\d+):.*B:(?P<btemp>[0-9.]+)\s*/(?P<bset>[0-9.]+).*T0:(?P<etemp>[0-9.]+)\s*/(?P<eset>[0-9.]+)')
# 1609027997: // probe at 175.000,175.000 is z=2.027500
PROBE_RE = re.compile(r'^(?P<ts>\d+):.*// probe at [0-9.,]+ is z=(?P<z>[0-9.]+)')


def parse_file(data_file):
    data = []
    with open(data_file) as f:
        for line in f:
            if START_RE.search(line):
                data = []
                continue

            m = TEMP_RE.match(line)
            if m:
                data.append({
                    'ts': int(m.group('ts')),
                    'btemp': float(m.group('btemp')),
                    'bset': float(m.group('bset')),
                    'etemp': float(m.group('etemp')),
                    'eset': float(m.group('eset'))
                })
                continue

            m = PROBE_RE.match(line)
            if m:
                data.append({
                    'ts': int(m.group('ts')),
                    'z': float(m.group('z'))
                })
                continue

    return data


def write_chart(data, output_file):
    min_ts = data[0]['ts']

    ztrace = pgo.Scatter(
        x=[x['ts'] - min_ts for x in data if 'z' in x],
        y=[x['z'] for x in data if 'z' in x],
        name='Z',
        mode='lines',
        line={'color': 'black'}
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

    fig = make_subplots(specs=[[{'secondary_y': True}]])
    fig.add_trace(ztrace, secondary_y=False)
    fig.add_trace(btrace, secondary_y=True)
    fig.add_trace(bstrace, secondary_y=True)
    fig.add_trace(etrace, secondary_y=True)
    fig.add_trace(estrace, secondary_y=True)
    fig.update_layout(title_text='Probe Accuracy')
    fig.update_xaxes(title_text='seconds')
    fig.update_yaxes(title_text='mm', secondary_y=False)
    fig.update_yaxes(title_text='°C', secondary_y=True)

    fig.write_html(output_file)


def main():
    args = parser.parse_args()

    data = parse_file(args.data_file)
    write_chart(data, args.output_file)


if __name__ == '__main__':
    main()

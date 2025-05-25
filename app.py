from collections import namedtuple
from typing import Iterable

from flask import Flask, render_template, request, jsonify
import json

app = Flask(__name__)

LOB_DETAILS = namedtuple('LOB', ['sub_lob', 'lob_code', 'vsad', 'composer'])
LOBS: dict[str, LOB_DETAILS] = {
    "wls": LOB_DETAILS("wireless", "vcg", "gk1v", "vz-it-wdwg-aidcom-0-cc-edw-wls-1"),
    "wln": LOB_DETAILS("wireline", "vcg", "gk1v", "vz-it-wdwg-aidcom-0-cc-edw-wls-1"),
    "vbg": LOB_DETAILS("vbg", "vbg", "zdwv", "vz-it-wdwg-aidcom-0-cc-edw-vbg-1"),
}


def clean_input(value: str) -> str:
    return value.strip().lower()


def clean_tables(tables: list[str]) -> str:
    updated_tables: list[str] = []
    for table in tables:
        if table.count('.') == 1:
            dataset, table = table.strip().lower().split('.', 1)
            dataset = 'db_' + dataset.removeprefix('db_')
            updated_tables.append('.'.join([dataset, table]))
        elif table.count('.') == 2:
            project_id, dataset, table = table.strip().lower().split('.', 2)
            dataset = 'db_' + dataset.removeprefix('db_')
            updated_tables.append('.'.join([project_id, dataset, table]))
    return ', '.join(updated_tables)


def clean_custom_tags(tags: list[str]) -> str:
    custom_tags: list[str] = []
    for tag in tags:
        tag = tag.strip()
        if not tag:
            continue
        key, value = tag.split(":", 1)
        custom_tags.append(key.strip().lower() + ":" + value.strip().lower())
    if custom_tags:
        return r'"' + '","'.join(custom_tags) + r'"'
    return ""


@app.route('/', methods=['GET', 'POST'])
def index():
    json_output = None
    selected_template = request.form.get('template_type_selection') if request.method == 'POST' else None

    if request.method == 'POST':
        if selected_template == 'Trigger DAG':
            context = {
                "lob": clean_input(request.form['lob']),
                "downstream_dag_id": clean_input(request.form['downstream_dag_id']),
                "opsgenie_priority": clean_input(request.form['opsgenie_priority']).upper(),
                "next_downstream_task_id": clean_input(request.form['next_downstream_task_id'])
            }
            json_output = render_template('dpf_templates/trigger_dag.json', **context)

        elif selected_template == 'Curation DAG Template':

            def schedule(sch: str) -> str:
                if sch.strip():
                    return "None"
                else:
                    return r'\"' + sch.strip() + r'\"'

            lob = clean_input(request.form['lob'])
            custom_tags: list[str] = [tag.strip() for tag in request.form.getlist('custom_tags') if tag.strip()]
            custom_tags = ',' + clean_custom_tags(custom_tags) if custom_tags else ''

            context = {
                "env": clean_input(request.form['environment']),
                "lob": lob,
                "lob_code": LOBS[lob].lob_code,
                "sub_lob": LOBS[lob].sub_lob,
                "vsad": LOBS[lob].vsad,
                "composer": LOBS[lob].composer,
                "espx_app_name": clean_input(request.form['espx_app_name']),
                "espx_job_name": clean_input(request.form['espx_job_name']),
                "target_table": clean_input(request.form['target_table']),
                "template_type": request.form['curation_template_type'].strip(),
                "schedule_interval": schedule(request.form['schedule_interval'].strip()),
                "custom_tags": custom_tags,
            }
            json_output = render_template('dpf_templates/curation_dag.json', **context)

        elif selected_template == 'External Task Sensor':
            context = {
                "external_dag_id": clean_input(request.form['external_dag_id']),
                "next_downstream_task_id": clean_input(request.form['next_downstream_task_id_sensor']),
                "dependency_timeout": int(request.form['dependency_timeout']),
                "opsgenie_priority": clean_input(request.form['opsgenie_priority_sensor']).upper()
            }
            json_output = render_template('dpf_templates/external_task_sensor.json', **context)

        elif selected_template == 'File Watcher':
            objects_list = [obj.strip() for obj in request.form.getlist('object') if obj.strip()]
            objects_json_string = json.dumps(objects_list)

            skip_on_file_not_found_bool = request.form['skip_on_file_not_found'].capitalize() == 'True'

            context = {
                "task_id": clean_input(request.form['task_id']),
                "objects": objects_json_string,
                "timeout": int(request.form['timeout']),
                "poke_interval": int(request.form['poke_interval']),
                "skip_on_file_not_found": str(skip_on_file_not_found_bool).lower(),
                "lob": clean_input(request.form['lob_file_watcher']),
                "opsgenie_priority": clean_input(request.form['opsgenie_priority_file_watcher']).upper(),
                "next_downstream_task_id": clean_input(request.form['next_downstream_task_id_file_watcher'])
            }
            json_output = render_template('dpf_templates/file_watcher.json', **context)

        elif selected_template == 'BQ Transform SQL':
            obs_source_tables_list = [tbl.strip() for tbl in request.form.getlist('obs_source_table') if tbl.strip()]
            obs_target_tables_list = [tbl.strip() for tbl in request.form.getlist('obs_target_table') if tbl.strip()]

            lob = clean_input(request.form['lob_bq_transform'])
            context = {
                "lob": LOBS[lob].sub_lob,
                "target_table": clean_input(request.form['target_table_bq_transform']),
                "sql_filename": clean_input(request.form['sql_filename_bq_transform']).removesuffix(".sql"),
                "espx_app_name": clean_input(request.form['espx_app_name_bq_transform']),
                "opsgenie_priority": clean_input(request.form['opsgenie_priority_bq_transform']).upper(),
                "gcp_conn_id": clean_input(request.form['gcp_conn_id_bq_transform']),
                "project_id": clean_input(request.form['project_id_bq_transform']),
                "obs_source_tables": clean_tables(obs_source_tables_list),
                "obs_target_tables": clean_tables(obs_target_tables_list),
                "next_downstream_task_id": clean_input(request.form['next_downstream_task_id_bq_transform'])
            }
            json_output = render_template('dpf_templates/bq_transform_sql.json', **context)

        if json_output:
            # print(json_output)
            json_output = json.dumps(json.loads(json_output), indent=2)

    return render_template('index.html', json_output=json_output, selected_template=selected_template)


if __name__ == '__main__':
    app.run(port=9000)

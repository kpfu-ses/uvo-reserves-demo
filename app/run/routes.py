from datetime import datetime

from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import current_user, login_required

from app import db
from app.helpers.services import save_run
from app.run import bp
from app.run.forms import RunForm
from app.microservices.main import get_wells_list
from app.models import Project, Run, Stratigraphy, Core


@bp.route('/runs/services', methods=['POST'])
@login_required
def choose_services():
    return jsonify({'wells': get_wells_list(request.form['services'], request.form['run_id'])})


@bp.route('/runs/<run_id>', methods=['GET', 'POST'])
@login_required
def run(run_id):
    this_run = Run.query.get(run_id)
    if this_run.exist():
        return redirect(url_for('run.run_view', run_id=this_run.id))
    return render_template('run/run.html', title='Run', run=this_run)


@bp.route('/runs/wells', methods=['POST'])
@login_required
def services_run():
    if current_user.get_task_in_progress('run_services'):
        flash('An export task is currently in progress')
    else:
        current_user.launch_task('run_services_task', 'Running services...', current_user.id, request.form['wells'],
                                 request.form['services'], request.form['run_id'])
        db.session.commit()
    return jsonify({'okay': 'okay'})


@bp.route('/run_view/<run_id>', methods=['GET'])
@login_required
def run_view(run_id):
    this_run = Run.query.filter_by(id=run_id).first()
    strats = list(Stratigraphy.query.filter_by(run_id=this_run.id))
    core_res = list(Core.query.filter_by(run_id=this_run.id))
    return render_template('run/run_view.html', title='Run', strats=strats, core_res=core_res)


@bp.route('/<project_id>/runs', methods=['GET', 'POST'])
@login_required
def runs(project_id):
    form = RunForm()
    project_runs = Project.query.get(project_id).runs()
    if form.validate_on_submit():
        this_run = save_run(project_id=project_id)
        return redirect(url_for('run.run', run_id=this_run.id))
    return render_template('run/runs.html', title='Runs', form=form, project_runs=project_runs)


@bp.route('/runs/done', methods=['GET'])
@login_required
def done_runs():
    done_runs_list = current_user.new_runs()
    current_user.last_run_see_time = datetime.now()
    db.session.commit()
    return render_template('run/done_runs.html', title='Done runs', runs=done_runs_list)
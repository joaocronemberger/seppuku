from logging.handlers import RotatingFileHandler
from flask import Flask, flash, redirect, render_template, request, session, abort
import json
import subprocess
import os
import os.path
import routes.gestor_dump_file
from routes import *
import sys
from pathlib import Path
import logging
import webbrowser
from time import strftime

app = Flask(__name__)
app.register_blueprint(routes)

@app.after_request
def after_request(response):
    """ Logging after every request. """
    # This avoids the duplication of registry in the log,
    # since that 500 is already logged via @app.errorhandler.
    if response.status_code != 500:
        ts = strftime('[%Y-%b-%d %H:%M]')
        logger.error('%s %s %s %s %s %s',
                      ts,
                      request.remote_addr,
                      request.method,
                      request.scheme,
                      request.full_path,
                      response.status)
    return response

@app.route('/')
def home():
    if not session.get('initialized'):
        inicializar()
    load_config()
    ler_argumentos()
    
    metodos_geral_alterado_tmp, metodos_geral_nao_alterado_tmp, metodos_totalizador_tmp = gestor_dump_file.get_report()
    return render_template('main.html', metodos_geral_alterado = metodos_geral_alterado_tmp,
                       metodos_geral_nao_alterado = metodos_geral_nao_alterado_tmp,
                       metodos_totalizador = metodos_totalizador_tmp)


@app.route('/getconfig', methods = ["POST"])
def get_config():

    compare_tool_full_path           = request.form.get('compare_tool_full_path')
    source_monitor_full_path         = request.form.get('source_monitor_full_path')
        
    if compare_tool_full_path:
        session['compare_tool_path'] = compare_tool_full_path
    if source_monitor_full_path:
        session['source_monitor_path'] = source_monitor_full_path
        
    data = {"compare_tool_path" : session.get('compare_tool_path'),
            "source_monitor_path" : session.get('source_monitor_path')}
    
    with open(session.get('settings_path'), 'w') as f:
        json.dump(data, f)
 
    return redirect('/')

@app.route('/open_compare_tool')
def open_compare_tool():
    validar_compare_tool()
    return redirect('/')

def validar_compare_tool():
    if gestor_dump_file.validar():
        subprocess.Popen(session.get('compare_tool_path') + " " + session.get('file_old') + " " + session.get('file_new'))
        
def load_config():
    path = Path().absolute()
    session['settings_path'] = str(path) + '\\settings.json'

    if not validar_file(session.get('settings_path')):
        return
    
    config                         = json.load(open( session.get('settings_path')))
    session['compare_tool_path']   = config["compare_tool_path"]
    session['source_monitor_path'] = config["source_monitor_path"]
            
    session['has_config']          = validar_file(session.get('compare_tool_path')) and validar_file(session.get('source_monitor_path'))

def validar_file(ps_file):
    if not ps_file:
        return False
    return (os.path.isfile(ps_file) and os.access(ps_file, os.R_OK))
        
def ler_argumentos():
    file_old = request.args.get('file_old')
    file_new = request.args.get('file_new')
    
    if not file_old or not file_new:
        return
    
    session['valid_files'] = (validar_file(file_old) and validar_file(file_new))
    session['file_new']    = file_new
    session['file_old']    = file_old
    
def inicializar():   
    sARQUIVO_NAO_LOCALIZADO = 'Arquivo não localizado!'
    session['initialized'] = True
    session['valid_files'] = False
    session['has_config']  = False
    session['file_new']    = sARQUIVO_NAO_LOCALIZADO
    session['file_old']    = sARQUIVO_NAO_LOCALIZADO

def get_port():

    try:  
        port = os.environ['PORTA_SEPPUKU']
    except KeyError: 
        port = 5000

    return int(port)

##Parte client - deve ser refatorado futuramente

def copia_arquivo(origem, destino):
    os.popen('copy "{origem}" "{destino}"'.format(origem=origem, destino=destino))
    
if (len(sys.argv) == 3):
    path_tmp = "Temp"
    tmp_tfs = "TFSTemp"
    tmp_smart = "smartgit-"
    
    path_tmp_seppuku = 'C:/Seppuku/Temp/'
    if not os.path.exists(path_tmp_seppuku):
        os.makedirs(path_tmp_seppuku)

    path_home_dir = os.environ['TEMP']
    name_file_old = os.path.basename(sys.argv[1])
    name_file_new = os.path.basename(sys.argv[2])
    
    arg1 = sys.argv[1]
    arg2 = sys.argv[2]
  
    file_old_temp = arg1
    file_new_temp = arg2

    
    if tmp_tfs in arg1 or tmp_smart in arg1:
        file_old_temp = path_tmp_seppuku + name_file_old
        copia_arquivo(arg1, file_old_temp)
    elif path_tmp in arg1:
        file_old_temp = path_tmp_seppuku + name_file_old
        arg1 = path_home_dir + '\\' + name_file_old
        copia_arquivo(arg1, file_old_temp)
        
    if tmp_tfs in arg2 or tmp_smart in arg2:
        file_new_temp = path_tmp_seppuku + name_file_new
        copia_arquivo(arg2, file_new_temp)
    elif path_tmp in arg2:
        file_new_temp = path_tmp_seppuku + name_file_new
        arg2 = path_home_dir + '\\' + name_file_new
        copia_arquivo(arg2, file_new_temp)
        

    file_new_temp = file_new_temp.replace('/', '\\')
    file_old_temp = file_old_temp.replace('/', '\\')      
    
    url = "http://127.0.0.1:{porta}?file_old={file_old}&file_new={file_new}".format(porta=get_port(), file_old=file_old_temp, file_new=file_new_temp)

    logging.info(url)
    webbrowser.open_new_tab(url)

if ((len(sys.argv) == 1) and (__name__ == "__main__")):
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)
    
    app.secret_key = os.urandom(12)
    app.run(host='127.0.0.1', port=get_port())
    
   


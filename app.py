HOST='0.0.0.0'
PORT=5078
BATCH=1
from flask import Flask, request, jsonify,send_file,Response,render_template
from pathlib import Path
import os,random,sys,threading, webbrowser, time,datetime,hashlib,tempfile,logging,subprocess,torch,glob,re,json
from waitress import serve
from flask_cors import CORS
from datetime import timedelta
from faster_whisper.audio import decode_audio
from faster_whisper.vad import (
    VadOptions,
    get_speech_timestamps
)

import traceback


ROOT_DIR=Path(__file__).parent.as_posix()
if sys.platform == 'win32':
    os.environ['PATH'] = ROOT_DIR + f';{ROOT_DIR}/ffmpeg;' + os.environ['PATH']



STATIC_DIR=f'{ROOT_DIR}/static'
LOGS_DIR=f'{ROOT_DIR}/logs'
TMP_DIR=f'{STATIC_DIR}/tmp'

Path(TMP_DIR).mkdir(parents=True, exist_ok=True)
Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_file_handler = logging.FileHandler(f'{LOGS_DIR}/{datetime.datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
_file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_file_handler.setFormatter(formatter)
logger.addHandler(_file_handler)

from pydub import AudioSegment
from fireredasr.models.fireredasr import FireRedAsr
import traceback

app = Flask(__name__, template_folder=f'{ROOT_DIR}/templates')
app.config['JSON_AS_ASCII'] = False  # 确保中文正确显示
CORS(app)

# 全局模型缓存
model_cache = {}

def load_models():
    """预加载模型到缓存中"""
    global model_cache
    logger.info("开始预加载模型...")
    
    # 检测可用设备
    if torch.cuda.is_available():
        device = torch.device('cuda')
        logger.info(f"检测到CUDA设备: {torch.cuda.get_device_name()}")
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = torch.device('mps')
        logger.info("检测到MPS设备 (Apple Silicon)")
    else:
        device = torch.device('cpu')
        logger.info("使用CPU设备")
    
    # PyTorch模型加载兼容性处理
    import argparse
    
    # 检查AED模型目录是否存在
    aed_model_dir = f'{ROOT_DIR}/pretrained_models/FireRedASR-AED-L'
    if Path(aed_model_dir).exists() and Path(f'{aed_model_dir}/dict.txt').exists():
        try:
            logger.info("加载AED模型...")
            model = FireRedAsr.from_pretrained('aed', aed_model_dir)
            model.model.to(device)  # 将模型移动到指定设备
            model_cache['AED'] = model
            logger.info(f"AED模型加载完成，已移动到设备: {device}")
        except Exception as e:
            logger.error(f"AED模型加载失败: {e}")
    else:
        logger.info("AED模型文件不完整，跳过预加载")
    
    # 检查LLM模型目录是否存在
    llm_model_dir = f'{ROOT_DIR}/pretrained_models/FireRedASR-LLM-L'
    llm_qwen_dir = f'{llm_model_dir}/Qwen2-7B-Instruct'
    if (Path(llm_model_dir).exists() and 
        Path(llm_qwen_dir).exists() and 
        Path(f'{llm_qwen_dir}/config.json').exists()):
        try:
            logger.info("加载LLM模型...")
            model = FireRedAsr.from_pretrained('llm', llm_model_dir)
            model.model.to(device)  # 将模型移动到指定设备
            model_cache['LLM'] = model
            logger.info(f"LLM模型加载完成，已移动到设备: {device}")
        except Exception as e:
            logger.error(f"LLM模型加载失败: {e}")
    else:
        logger.info("LLM模型文件不完整，跳过预加载")
    
    logger.info(f"模型预加载完成，已加载模型: {list(model_cache.keys())}")

# 将字符串做 md5 hash处理
def get_md5(input_string):
    md5 = hashlib.md5()
    md5.update(input_string.encode('utf-8'))
    return md5.hexdigest()

def runffmpeg(cmd):
    
    try:
        if cmd[0]!='ffmpeg':
            cmd.insert(0,'ffmpeg')
        logger.info(f'{cmd=}')
        subprocess.run(cmd,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       encoding="utf-8",
                       check=True,
                       text=True,
                       creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW)

    except Exception as e:
        # 检查异常是否为 subprocess.CalledProcessError 类型,该类型包含 stderr 属性
        if isinstance(e, subprocess.CalledProcessError):
            raise Exception(str(e.stderr))
        else:
            raise Exception(f'执行Ffmpeg操作失败:{cmd=}')
    return True

'''
格式化毫秒或秒为符合srt格式的 2位小时:2位分:2位秒,3位毫秒 形式
print(ms_to_time_string(ms=12030))
-> 00:00:12,030
'''


def ms_to_time_string(*, ms=0, seconds=None):
    # 计算小时、分钟、秒和毫秒
    if seconds is None:
        td = timedelta(milliseconds=ms)
    else:
        td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000

    time_string = f"{hours}:{minutes}:{seconds},{milliseconds}"
    return format_time(time_string, ',')


# 将不规范的 时:分:秒,|.毫秒格式为  aa:bb:cc,ddd形式
# eg  001:01:2,4500  01:54,14 等做处理
def format_time(s_time="", separate=','):
    if not s_time.strip():
        return f'00:00:00{separate}000'
    hou, min, sec, ms = 0, 0, 0, 0

    tmp = s_time.strip().split(':')
    if len(tmp) >= 3:
        hou, min, sec = tmp[-3].strip(), tmp[-2].strip(), tmp[-1].strip()
    elif len(tmp) == 2:
        min, sec = tmp[0].strip(), tmp[1].strip()
    elif len(tmp) == 1:
        sec = tmp[0].strip()

    if re.search(r'[,.]', str(sec)):
        t = re.split(r'[,.]', str(sec))
        sec = t[0].strip()
        ms = t[1].strip()
    else:
        ms = 0
    hou = f'{int(hou):02}'[-2:]
    min = f'{int(min):02}'[-2:]
    sec = f'{int(sec):02}'
    ms = f'{int(ms):03}'[-3:]
    return f"{hou}:{min}:{sec}{separate}{ms}"

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_file(f'{STATIC_DIR}/{filename}')


@app.route('/')
def index():
    return jsonify({
        "message": "FireRedASR API Server",
        "version": "1.0",
        "endpoints": {
            "/v1/audio/transcriptions": "POST - 语音识别接口"
        },
        "usage": "使用POST方法向/v1/audio/transcriptions发送音频文件进行识别"
    })



@app.route('/v1/audio/transcriptions', methods=['POST','GET'])
def uploadfile():
    try:
        if 'file' not in request.files:  # 检查是否上传了文件
            error_json = json.dumps({"code": 1, 'error': 'No file part'}, ensure_ascii=False)
            return Response(error_json, status=500, mimetype='application/json; charset=utf-8')

        file = request.files['file']
        if file.filename == '':  # 检查是否选择了文件
            error_json = json.dumps({"code": 1, 'error': 'No selected file'}, ensure_ascii=False)
            return Response(error_json, status=500, mimetype='application/json; charset=utf-8')
        response_format=request.form.get('response_format','srt')
        model=request.form.get('model','AED').upper()
        if model not in ['AED','LLM']:
            model='AED'
        
        print(f'{model=}')
        if not Path(f'{ROOT_DIR}/pretrained_models/FireRedASR-{model}-L/model.pth.tar').exists():
            error_json = json.dumps({"code": 2, 'error': f'请下载 {model} 模型并放入 {ROOT_DIR}/pretrained_models/FireRedASR-{model}-L/'}, ensure_ascii=False)
            return Response(error_json, status=500, mimetype='application/json; charset=utf-8')

        # 获取文件扩展名
        # 使用时间戳生成文件名
        name=f'{time.time()}'
        # 获取文件扩展名,需要将filename转为str类型
        ext=os.path.splitext(str(file.filename))[1]
        filename_raw = f'{TMP_DIR}/raw-{name}{ext}'
        filename_16k = f'{TMP_DIR}/16k-{name}.wav'
        # 创建目录
        target_dir = f'{TMP_DIR}/{name}'
        Path(target_dir).mkdir(parents=True, exist_ok=True)
        file.save(filename_raw)
        # 保存文件到 /tmp 目录
        runffmpeg(['-y', '-i', filename_raw,'-ac','1','-ar','16000', '-c:a', 'pcm_s16le','-f','wav', filename_16k])
        file_length=len(AudioSegment.from_file(filename_16k,format=filename_16k[-3:]))
        if file_length>=30000:
            wavs=cut_audio(filename_16k,target_dir)
        else:
            wavs=[{
                "line":1,
                "start_time":0,
                "end_time":file_length,
                "file":filename_16k,
                "text":"",
                'uttid':f'0_{file_length}',
                'startraw':'00:00:00,000',
                'endraw':ms_to_time_string(ms=file_length),
            }]
        srts=asr_task(wavs,asr_type=model)
        if response_format == 'text':
            return Response(". ".join([it['text'] for it in srts]), mimetype='text/plain')
        if response_format=='json':
            result_json = json.dumps({"text":". ".join([it['text'] for it in srts])}, ensure_ascii=False)
            return Response(result_json, mimetype='application/json; charset=utf-8')
        result=[f"{it['line']}\n{it['startraw']} --> {it['endraw']}\n{it['text']}" for it in srts]
        return Response("\n\n".join(result), mimetype='text/plain')
    except Exception as e:
        error_json = json.dumps({"code": 1, 'error': str(e)}, ensure_ascii=False)
        return Response(error_json, status=500, mimetype='application/json; charset=utf-8')

def asr_task(wavs,asr_type='AED'):
    # 使用缓存的模型，如果缓存中没有则动态加载
    global model_cache
    
    # 检测设备
    if torch.cuda.is_available():
        device = torch.device('cuda')
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = torch.device('mps')
    else:
        device = torch.device('cpu')
    
    if asr_type in model_cache:
        model = model_cache[asr_type]
        logger.info(f"使用缓存的{asr_type}模型")
    else:
        logger.info(f"缓存中没有{asr_type}模型，动态加载...")
        model = FireRedAsr.from_pretrained(asr_type.lower(), f'{ROOT_DIR}/pretrained_models/FireRedASR-{asr_type}-L')
        model.model.to(device)  # 将动态加载的模型也移动到设备
        model_cache[asr_type] = model  # 加载后放入缓存
        logger.info(f"动态加载的{asr_type}模型已移动到设备: {device}")
    
    idxs={}
    for i,it in enumerate(wavs):
        idxs[it['uttid']]=i
    wavs_chunks=[wavs[i:i+BATCH] for i in range(0,len(wavs),BATCH)]
    param={
        "device": device,
        "beam_size": 1,
        "nbest": 1,
        "decode_max_len": 0,
        "softmax_smoothing": 1.0,
        "aed_length_penalty": 0.0,
        "decode_min_len": 0,
        "repetition_penalty": 1.0,
        "llm_length_penalty": 0.0,
        "eos_penalty": 1.0,
        "temperature": 1.0
    }
    for it in wavs_chunks:
        results = model.transcribe(
            [em['uttid'] for em in it],
            [em['file'] for em in it],
            param
        )
        # 确保results是可迭代对象
        if isinstance(results, dict):
            results = [results]
        # 确保results是列表类型,如果是None则使用空列表
        for result in (results if results is not None else []):
            # 使用索引获取wavs列表中对应的字典,然后更新text字段
            # 使用get方法安全地获取uttid对应的索引,如果不存在则返回-1
            idx = idxs.get(result.get('uttid', ''), -1)
            if 0 <= idx < len(wavs):
                # 检查并确保索引和键的存在性
                if idx < len(wavs) and 'text' in result:
                    wavs[idx]['text'] = result.get('text', '')
    return wavs


def openurl(url):
    def op():
        time.sleep(5)
        try:

            webbrowser.open_new_tab(url)
        except:
            pass

    threading.Thread(target=op).start()


# 根据 时间开始结束点，切割音频片段,并保存为wav到临时目录，记录每个wav的绝对路径到list，然后返回该list
def cut_audio(audio_file,dir_name):
    sampling_rate=16000
    

    def convert_to_milliseconds(timestamps):
        milliseconds_timestamps = []
        for timestamp in timestamps:
            milliseconds_timestamps.append(
                {
                    "start": int(round(timestamp["start"] / sampling_rate * 1000)),
                    "end": int(round(timestamp["end"] / sampling_rate * 1000)),
                }
            )

        return milliseconds_timestamps
    vad_p={
        "threshold":  0.5,
        "neg_threshold": 0.35,
        "min_speech_duration_ms":  0,
        "max_speech_duration_s":  float("inf"),
        "min_silence_duration_ms": 250,
        "speech_pad_ms": 200
    }
    # 解码音频文件并获取音频数据
    audio_data = decode_audio(audio_file, sampling_rate=sampling_rate)
    # 如果返回的是元组,取第一个元素作为音频数据
    if isinstance(audio_data, tuple):
        audio_data = audio_data[0]
    speech_chunks = get_speech_timestamps(audio_data, vad_options=VadOptions(**vad_p))
    speech_chunks=convert_to_milliseconds(speech_chunks)
    
    data=[]
    audio = AudioSegment.from_wav(audio_file)
    for i,it in enumerate(speech_chunks):
        start_ms, end_ms=it['start'],it['end']
        chunk = audio[start_ms:end_ms]
        file_name=f"{dir_name}/{start_ms}_{end_ms}.wav"
        chunk.export(file_name, format="wav")
        data.append({
        "line":i+1,
        "start_time":start_ms,
        "end_time":end_ms,
        "file":file_name,
        "text":"",
        'uttid':f'{start_ms}_{end_ms}',
        'startraw':ms_to_time_string(ms=start_ms),
        'endraw':ms_to_time_string(ms=end_ms),
        })

    return data
 



if __name__ == '__main__':
    try:
        # 预加载模型
        load_models()
        
        print(f"api接口地址  http://{HOST}:{PORT}")
        openurl(f'http://{HOST}:{PORT}')
        serve(app, host=HOST, port=PORT,threads=4)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        logger.error(traceback.format_exc())
    


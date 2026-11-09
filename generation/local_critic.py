"""OpenAI-compatible sampled-frame adapter for Code2Video's original visual Critic.

This is an explicit model/input adaptation: sampled frames replace the original
provider's native video input. It must not be reported as the original model's
paper score or as direct audio inspection.
"""
import hashlib,json,os,uuid
from pathlib import Path


def request(prompt,video_path,image_path=None,log_id=None,max_tokens=2500,max_retries=1):
    from openai import OpenAI
    from PIL import Image
    from eval.frame_extractor import extract_frames,frames_as_multimodal_content,frame_to_data_url
    from generation.prompt_budget import request_budget
    path=Path(video_path)
    frames=extract_frames(str(path),n=8,resize_max=832)
    instruction=('Inspect these actual ordered video samples. The final extra image, when supplied, '
        'is the author reference grid, not a video frame. Preserve the original task, givens, '
        'object identities, scientific meaning and source restrictions. Give localized actionable '
        'layout fixes supported by the frames; do not invent defects or add unrelated content. '
        'Do not target a favorable or unfavorable score.\n'+prompt)
    content=frames_as_multimodal_content(frames,instruction)
    grid=Path(image_path) if image_path else None
    if grid and grid.is_file():
        with Image.open(grid) as im:
            reference=im.convert('RGB');reference.thumbnail((832,832))
            content += [{'type':'text','text':'Author reference grid:'},
                        {'type':'image_url','image_url':{'url':frame_to_data_url(reference)}}]
    budget,_=request_budget(instruction,min(max_tokens,2500),len(frames)+int(bool(grid and grid.is_file())))
    base=os.getenv('LOCAL_BASE_URL','http://127.0.0.1:8000/v1');model=os.getenv('LOCAL_MODEL','qwen3.8-27b')
    response=OpenAI(base_url=base,api_key=os.getenv('LOCAL_API_KEY','local'),timeout=600,max_retries=max_retries).chat.completions.create(
        model=model,messages=[{'role':'user','content':content}],max_tokens=budget,temperature=.2,
        extra_body={'chat_template_kwargs':{'enable_thinking':False}})
    if response.choices[0].finish_reason=='length':raise ValueError('visual Critic response truncated')
    output=path.parent/'critic_calls';output.mkdir(exist_ok=True)
    (output/(str(log_id or uuid.uuid4().hex)+'.json')).write_text(json.dumps({
        'model':model,'base_url':base,'video_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'sample_count':len(frames),'reference_grid':str(grid) if grid else None,
        'input_adaptation':'8 ordered sampled frames plus optional author grid; no direct audio',
        'prompt':instruction,'response':response.choices[0].message.content,
        'usage':response.usage.model_dump() if response.usage else {}},ensure_ascii=False,indent=2)+'\n')
    return response

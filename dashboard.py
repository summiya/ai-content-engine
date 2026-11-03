import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
from datetime import datetime

import streamlit as st
import content_engine as engine

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "output" / "ui_jobs"
JOBS.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="AI Content Engine", page_icon="✦",
                   layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {background:#0D1115;color:#F6F3EC}
.block-container {max-width:1240px;padding-top:1.7rem}
[data-testid="stHeader"] {background:transparent}
h1,h2,h3 {letter-spacing:-0.035em}
h1 {font-size:3.2rem!important}
div[data-testid="stButton"] button {border-radius:12px;min-height:46px;font-weight:650}
div[data-testid="stButton"] button[kind="primary"] {background:#D7F3A3;color:#182313;border:0}
div[data-testid="stMetric"] {padding:15px;border:1px solid #303B3C;border-radius:14px;background:#172021}
div[data-testid="stImage"] img {border-radius:14px}
.hero {background:linear-gradient(120deg,#243C31,#151D20 70%);border:1px solid #394D40;
border-radius:20px;padding:30px 34px;margin:12px 0 23px}
.hero h1 {margin:10px 0 14px}
.kicker {color:#D7F3A3;letter-spacing:.18em;font-size:12px;font-weight:800}
.tagline {color:#B8C5BA}
</style>
""", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state.page = "Create Images"

st.markdown("✦  **AI CONTENT ENGINE** &nbsp; / &nbsp; LOCAL STUDIO")
nav = st.columns([1,1,1,2])
for column, label, mark in zip(nav[:3], ["Create Images","Instagram","Automation"], ["✦","◎","◷"]):
    with column:
        if st.button(mark + "  " + label, key="nav_"+label, use_container_width=True,
                     type="primary" if st.session_state.page == label else "secondary"):
            st.session_state.page = label
            st.rerun()
st.divider()


def job_files():
    return sorted(JOBS.glob("*.json"), key=lambda p:p.stat().st_mtime, reverse=True)


def get_job(path):
    try:
        return json.loads(path.read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError):
        return None


def gallery():
    result = []
    for jobpath in job_files():
        job = get_job(jobpath)
        if not job:
            continue
        for item in reversed(job.get("images", [])):
            p = (ROOT/item["path"]).resolve()
            if p.is_file() and p.is_relative_to(ROOT/"output"):
                result.append((p, item))
    return result


def hero(kicker, title, detail):
    st.markdown(
        '<div class="hero"><div class="kicker">'+kicker+'</div><h1>'+title+
        '</h1><p class="tagline">'+detail+'</p></div>',
        unsafe_allow_html=True)


def create_images():
    hero("01 / CREATIVE WORKSPACE", "Create something remarkable.",
         "Design product images on your own Mac. Preview each result in your local gallery. Nothing is posted.")
    m1,m2,m3 = st.columns(3)
    m1.metric("Model", "FLUX.2 Klein 4B")
    m2.metric("API cost", "$0")
    m3.metric("Images in gallery", len(gallery()))
    left,right = st.columns([1,1.35],gap="large")
    with left:
        st.subheader("Create images")
        subject = st.selectbox("Product", ["Mixed products","Sofa","Bed","Side table",
            "Armchair","Coffee table","Lamp","Vase","Handbag","Decorative stool","Custom subject"])
        if subject == "Custom subject":
            subject = st.text_input("Describe the item", value="sculptural table lamp")
        style = st.selectbox("Photography style",["Clean neutral studio","Warm minimalist",
                                                  "Luxury editorial","Soft daylight","Monochrome studio"])
        instructions = st.text_area("Creative direction (optional)",max_chars=700,
                                    placeholder="Curved silhouette, pale fabric, off-white studio")
        amount = st.select_slider("Number of images",options=[1,2,5,10,20],value=1)
        jobs = job_files()
        latest = get_job(jobs[0]) if jobs else None
        busy = bool(latest and latest.get("state") in ("queued","running"))
        if busy:
            st.info("A generation job is currently running.")
        installed = bool(shutil.which("mflux-generate-flux2"))
        if not installed:
            st.warning("Install MFLUX on your Mac first using the local AI installer.")
        if st.button("✦  Generate images",type="primary",use_container_width=True,
                     disabled=busy or not installed or not subject.strip()):
            key = str(uuid.uuid4())
            jobpath = JOBS/(key+".json")
            jobpath.write_text(json.dumps({"id":key,"state":"queued","count":amount,
                "completed":0,"images":[],"created_at":datetime.now().isoformat()},
                indent=2),encoding="utf8")
            command = [sys.executable,str(ROOT/"ui_generate.py"),"--job",key,
                       "--count",str(amount),"--subject",subject,"--style",style,
                       "--instructions",instructions]
            with (ROOT/"logs"/"ui-worker.log").open("a",encoding="utf8") as log:
                subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                                 start_new_session=True)
            st.rerun()
        st.caption("Generates one image at a time; the model download on first use may be large.")
    with right:
        st.subheader("Live preview")
        @st.fragment(run_every="3s")
        def progress_view():
            jobs = job_files()
            job = get_job(jobs[0]) if jobs else None
            if not job:
                st.info("Choose a product and click Generate images to begin.")
                return
            finished = job.get("completed",0)
            total = max(1,job.get("count",1))
            state = job.get("state","queued")
            st.progress(min(1,finished/total),text=f"{finished} / {total} complete · {state.title()}")
            if state == "failed":
                st.error(job.get("error","Generation failed. Inspect logs/ui-worker.log"))
            elif state == "finished":
                st.success("Generation complete. Saved on your Mac.")
            elif state in ("queued","running"):
                st.caption("Rendering locally. New images appear as they finish.")
            if job.get("images"):
                image = ROOT/job["images"][-1]["path"]
                if image.is_file():
                    st.image(str(image),caption="Latest result",use_container_width=True)
            else:
                st.info("Your first image will appear here.")
        progress_view()
    st.divider()
    st.subheader("Image gallery")
    images = gallery()
    if not images:
        st.info("Your gallery is empty.")
    for idx in range(0,min(36,len(images)),3):
        columns = st.columns(3)
        for col,(image,item) in zip(columns,images[idx:idx+3]):
            with col:
                st.image(str(image),use_container_width=True)
                st.caption(item.get("category","Product"))
                st.download_button("↓ Download JPEG",data=image.read_bytes(),
                                   file_name=image.name,mime="image/jpeg",
                                   key="download_"+str(image),use_container_width=True)
                with st.expander("Prompt"):
                    st.write(item.get("prompt",""))
                if st.button("Add to Instagram queue", key="queue_"+item["id"],
                             use_container_width=True):
                    with engine.single_instance():
                        db = engine.load_db()
                        if any(x.get("source_id")==item["id"] for x in db["items"]):
                            st.info("This image is already in the queue.")
                        else:
                            now = engine.now()
                            post = {
                                "id":str(uuid.uuid4()),"source_id":item["id"],
                                "day":now.date().isoformat(),"seq":len(db["items"])+1,
                                "category":item["category"],"title":item["category"].title()+" Concept",
                                "prompt":item["prompt"],"path":str(image.relative_to(ROOT)),
                                "schedule":now.isoformat(),"status":"ready"
                            }
                            post["caption"]=engine.fallback_caption(post)
                            db["items"].append(post)
                            engine.save_db(db)
                            st.success("Added to queue. Not published.")


def instagram():
    hero("02 / PUBLISHING WORKSPACE","Instagram publishing.",
         "An optional connection to the official Instagram API. Nothing posts automatically from this dashboard.")
    st.info("Local gallery images are never automatically published. This section only accesses the separate legacy publishing queue.")
    pending = [x for x in engine.load_db()["items"]
        if x.get("status") in ("ready","uploaded","container_created")
        and x.get("path") and (ROOT/x["path"]).is_file()]
    with st.expander("Connection checklist"):
        st.write("Configure IG_USER_ID, META_ACCESS_TOKEN, and CLOUDINARY_URL in your local environment file. A professional Instagram account is required.")
    if not pending:
        st.warning("No queued Instagram posts. Use the existing command-line content queue if you want to prepare publishing.")
        return
    names = [f"{i+1}. {p['title']} ({p['status']})" for i,p in enumerate(pending)]
    selected = st.selectbox("Choose a queued post",names)
    post = pending[names.index(selected)]
    st.image(str(ROOT/post["path"]),width=370)
    st.text_area("Caption",post.get("caption",""),height=160,disabled=True)
    confirm = st.checkbox("I explicitly authorize publishing this exact post now.")
    if st.button("Publish this post",type="primary",disabled=not confirm):
        try:
            if not all(os.getenv(k) for k in ("IG_USER_ID","META_ACCESS_TOKEN","CLOUDINARY_URL")):
                raise RuntimeError("Missing Meta or Cloudinary configuration")
            with engine.single_instance():
                engine.quota_check()
                engine.instagram_publish(post)
            st.success("Post published.")
        except Exception as exc:
            st.error(str(exc))
            st.warning("Check Instagram before retrying to avoid duplicates.")


def automation():
    hero("03 / SCHEDULING CENTER","Automate on your schedule.",
         "Choose your daily target, save the settings, and optionally enable Mac scheduling.")
    st.info("Auto-publishing remains disabled unless you deliberately change AUTO_PUBLISH in your private configuration.")
    env_path = ROOT/".env"
    if not env_path.exists():
        st.warning("Run the Mac installer first to create your local configuration.")
        return
    with st.form("scheduler_settings"):
        daily_target = st.select_slider("Daily image target", options=[1,2,5,10,15,20],
            value=min([1,2,5,10,15,20], key=lambda n:abs(n-int(os.getenv("DAILY_COUNT","20")))))
        a,b=st.columns(2)
        with a:
            first=st.selectbox("Posting window starts",list(range(0,23)),
                index=min(22,int(os.getenv("POST_START_HOUR","8"))))
        with b:
            last=st.selectbox("Posting window ends",list(range(1,24)),
                index=min(22,max(0,int(os.getenv("POST_END_HOUR","22"))-1)))
        submitted=st.form_submit_button("Save schedule settings",use_container_width=True)
    if submitted:
        if first >= last:
            st.error("The end hour must be later than the start hour.")
        else:
            from dotenv import set_key
            set_key(str(env_path),"DAILY_COUNT",str(daily_target))
            set_key(str(env_path),"POST_START_HOUR",str(first))
            set_key(str(env_path),"POST_END_HOUR",str(last))
            st.success("Settings saved. Restart the dashboard to refresh its displayed values.")
    st.divider()
    st.subheader("Local Mac scheduler")
    st.write("The LaunchAgent checks every 15 minutes while the Mac is awake and logged in.")
    confirm = st.checkbox("I understand that enabling this will start scheduled local jobs.")
    a,b=st.columns(2)
    with a:
        if st.button("Enable scheduler",disabled=not confirm,use_container_width=True):
            result=subprocess.run(["/bin/zsh",str(ROOT/"enable_mac_schedule.sh")],
                                  cwd=ROOT,capture_output=True,text=True,timeout=30)
            if result.returncode==0:
                st.success("Mac scheduler enabled.")
            else:
                st.error(result.stderr or result.stdout)
    with b:
        if st.button("Disable scheduler",use_container_width=True):
            result=subprocess.run(["/bin/zsh",str(ROOT/"disable_mac_schedule.sh")],
                                  cwd=ROOT,capture_output=True,text=True,timeout=30)
            if result.returncode==0:
                st.success("Mac scheduler disabled.")
            else:
                st.error(result.stderr or result.stdout)
    st.caption("The scheduler runs the existing queue engine, not UI generation jobs. "
               "Published posts require separate Instagram credentials and AUTO_PUBLISH=true.")

if st.session_state.page=="Create Images":
    create_images()
elif st.session_state.page=="Instagram":
    instagram()
else:
    automation()
st.divider()
st.caption("AI Content Engine · Local-only dashboard · No automatic publishing while testing")

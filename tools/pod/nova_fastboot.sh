# tools/pod/nova_fastboot.sh -- NOVA-FASTBOOT (2026-11-22). SOURCED by nova_final_pod.sh only when NF_VOLUME_DIR is set
# (nova_play.py / nova_final_ctl.py with NF_VOLUME=<network volume id>). Default (unset) = today's boot, unchanged.
#
# Why: every NOVA-FINAL boot spent 9-31 min pulling the 14.3 GB private image before the first STAGES line. The fast
# way boots the common runpod/pytorch image (cached on RunPod hosts, the co-host's 17-26 s boots) and takes the heavy
# parts from Nova's network volume, all under <volume>/nova-fastboot/ (nothing else on the volume is read or touched):
#   packs/ltenv.tar   /opt/ltenv (SoulX python env, torch 2.6 + livekit/playwright) + /opt/maya-ops  -> unpacked to local disk
#   packs/ditto.tar   /workspace/ditto (the Ditto pack, unpacked: venv + TRT engines + weights)       -> unpacked to local disk
#   soulxroot/        the SoulX-FlashHead weights + code + ACTIVATE.sh  (/opt/soulxroot -> here, read in place)
#   cache/inductor, cache/triton   torch.compile caches: the SoulX warm-up compiles once, later boots reuse it
# NO SILENT FALLBACK: a part that is missing is said in STAGES as "VOLUME PART MISSING: <part> - fetching", fetched the
# old way (ltenv from the image's own layers via nfb_layers.py, Ditto from its GitHub pack, weights from Hugging Face),
# and saved to the volume at the end of the run, so the next boot has it. Packs are only ever ADDED (write .tmp, then
# rename); this script never deletes anything on the volume.
NFB_V=$NF_VOLUME_DIR/nova-fastboot; NFB_P=$NFB_V/packs
if [ ! -d "$NF_VOLUME_DIR" ]; then stage "NFB FAILED: NF_VOLUME_DIR=$NF_VOLUME_DIR is not mounted"; fi
mkdir -p "$NFB_P" "$NFB_V/cache/inductor" "$NFB_V/cache/triton" "$NFB_V/soulxroot"
stage "nfb volume $NF_VOLUME_DIR: $(df -h "$NF_VOLUME_DIR" | tail -1 | awk '{print $2" size, "$3" used, "$4" free"}'); top: $(ls "$NF_VOLUME_DIR" | tr '\n' ' ' | cut -c1-300); packs: $(cd "$NFB_P" && ls | tr '\n' ' ')"
( cd "$NF_VOLUME_DIR" && timeout 300 du -sh -- * .[!.]* 2>/dev/null; echo; timeout 120 du -sh "$NFB_V"/* "$NFB_V"/packs/* 2>/dev/null ) > $OUT/nfb_volume_list.txt 2>&1 &
export TORCHINDUCTOR_CACHE_DIR=$NFB_V/cache/inductor TRITON_CACHE_DIR=$NFB_V/cache/triton TORCHINDUCTOR_FX_GRAPH_CACHE=1 \
       TORCHINDUCTOR_AUTOGRAD_CACHE=1 PYTHONUTF8=1 SOULX_ROOT=/opt/soulxroot
rm -f /root/nfb_ltenv.done /root/nfb_save_ltenv /root/nfb_save_ditto

# (1) the SoulX python env + maya-ops code
( t=$(date +%s)
  if [ -s "$NFB_P/ltenv.ok" ] && [ -s "$NFB_P/ltenv.tar" ]; then
    tar -xf "$NFB_P/ltenv.tar" -C / && stage "nfb ltenv: volume pack $(du -h "$NFB_P/ltenv.tar" | cut -f1) unpacked in $(( $(date +%s) - t )) s" \
      || stage "NFB FAILED: ltenv pack did not unpack (rc $?)"
  else
    stage "VOLUME PART MISSING: ltenv - fetching from the image layers (nfb_layers.py)"; touch /root/nfb_save_ltenv
    python3 $R/tools/pod/nfb_layers.py / > $OUT/nfb_layers.log 2>&1; stage "nfb ltenv: image layers rc=$? in $(( $(date +%s) - t )) s ($(tail -1 $OUT/nfb_layers.log | cut -c1-160))"
  fi; touch /root/nfb_ltenv.done ) &
NFB_LPID=$!

# (2) the SoulX weights, read in place from the volume
[ -e /opt/soulxroot ] && [ ! -L /opt/soulxroot ] && stage "NFB NOTE: /opt/soulxroot already in the image; using the volume copy instead" && mv /opt/soulxroot /opt/soulxroot.image
ln -sfn "$NFB_V/soulxroot" /opt/soulxroot
( if [ -s /opt/soulxroot/ACTIVATE.sh ] && [ -d /opt/soulxroot/models/SoulX-FlashHead-1_3B ]; then echo "weights baked (volume $NFB_V/soulxroot)" > $OUT/weights.txt
  else stage "VOLUME PART MISSING: SoulX weights - fetching to the volume"; echo "weights NOT baked - fetching to the volume" > $OUT/weights.txt
    for i in $(seq 1 600); do [ -f /root/nfb_ltenv.done ] && break; sleep 1; done
    timeout 1200 python3 /opt/maya-ops/lt/soulx_fetch.py --root /opt/soulxroot --jobs 4 >> $OUT/weights.txt 2>&1; fi ) &
WPID=$!

# (3) Ditto: unpack the volume copy, then the usual ditto_up.sh (it sees .env_ok and only starts the server)
nfb_ditto_start(){
  ( t=$(date +%s)
    if [ -s "$NFB_P/ditto.ok" ] && [ -s "$NFB_P/ditto.tar" ]; then
      mkdir -p /workspace && tar -xf "$NFB_P/ditto.tar" -C /workspace && stage "nfb ditto: volume pack $(du -h "$NFB_P/ditto.tar" | cut -f1) unpacked in $(( $(date +%s) - t )) s" \
        || stage "NFB FAILED: ditto pack did not unpack (rc $?)"
    else stage "VOLUME PART MISSING: ditto - fetching the GitHub pack ($DITTO_PACK)"; touch /root/nfb_save_ditto; fi
    for i in 1 2; do bash $R/tools/pod/ditto_take8/ditto_up.sh > $OUT/ditto_up.log 2>&1 && break; sleep 5; done
    echo "rc=$? after $(( $(date +%s) - t )) s" >> $OUT/ditto_up.log ) &
  DPID=$!
}

# (4) before the first use of $PY: wait for the env, check it, point PY/MO at it
nfb_wait_ltenv(){
  wait $NFB_LPID
  PY=/opt/ltenv/bin/python; MO=/opt/maya-ops/lt; export FACE_RENDERER_DIR=$MO
  stage "nfb ltenv check: $($PY -c 'import torch, diffusers, cv2; print("torch", torch.__version__, "cuda", torch.cuda.is_available(), "diffusers", diffusers.__version__)' 2>&1 | tail -1 | cut -c1-200)"
}

# (5) end of the run: save what was fetched, so the next boot has it (add-only)
nfb_save(){
  t=$(date +%s)
  if [ -f /root/nfb_save_ltenv ]; then
    tar -cf "$NFB_P/ltenv.tar.tmp" -C / opt/ltenv opt/maya-ops && mv "$NFB_P/ltenv.tar.tmp" "$NFB_P/ltenv.tar" && date -u > "$NFB_P/ltenv.ok" \
      && stage "nfb saved ltenv.tar $(du -h "$NFB_P/ltenv.tar" | cut -f1) in $(( $(date +%s) - t )) s" || stage "NFB FAILED: saving ltenv.tar"
  fi
  t=$(date +%s)
  if [ -f /root/nfb_save_ditto ] && [ -s /workspace/ditto/.env_ok ]; then
    tar -cf "$NFB_P/ditto.tar.tmp" -C /workspace ditto && mv "$NFB_P/ditto.tar.tmp" "$NFB_P/ditto.tar" && date -u > "$NFB_P/ditto.ok" \
      && stage "nfb saved ditto.tar $(du -h "$NFB_P/ditto.tar" | cut -f1) in $(( $(date +%s) - t )) s" || stage "NFB FAILED: saving ditto.tar"
  fi
  stage "nfb volume after: $(df -h "$NF_VOLUME_DIR" | tail -1 | awk '{print $3" used, "$4" free"}'); nova-fastboot $(timeout 120 du -sh "$NFB_V" | cut -f1); caches inductor $(timeout 60 du -sh "$NFB_V/cache/inductor" | cut -f1) triton $(timeout 60 du -sh "$NFB_V/cache/triton" | cut -f1)"
}

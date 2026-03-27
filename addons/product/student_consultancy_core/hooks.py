def post_init_hook(env):
    env["student.consultancy.mode"].apply_curated_mode()

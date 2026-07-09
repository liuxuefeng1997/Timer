class TencentCloud:
    class Update:
        # 本体更新
        update_region = "ap-shanghai"
        update_bukkit = "update-1251534239"
        update_cosDir = "Timer"
        update_manifest = "gui_version.json"
        update_channel_list = "gui_channel.json"

        self_update_manifest_url = "https://"f"{update_bukkit}.cos.{update_region}.myqcloud.com/{update_cosDir}/{update_manifest}"
        self_update_url = "https://"f"{update_bukkit}.cos.{update_region}.myqcloud.com/{update_cosDir}/"
        self_update_channel_list_url = "https://"f"{update_bukkit}.cos.{update_region}.myqcloud.com/{update_cosDir}/{update_channel_list}"


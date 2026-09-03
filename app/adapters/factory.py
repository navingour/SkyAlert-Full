from typing import Dict, Any, List
from app.adapters.base import BaseInputAdapter
from app.adapters.tar1090_http import Tar1090HttpAdapter
from app.adapters.readsb_json import ReadsbJsonAdapter
from app.adapters.sbs_tcp import SbsTcpAdapter
from app.adapters.beast_tcp import BeastTcpAdapter
from app.logger import logger


class AdapterFactory:

    @staticmethod
    def create_adapter(source_id: str, adapter_type: str, name: str, config: Dict[str, Any]) -> BaseInputAdapter:
        adapter_type = adapter_type.lower()
        if adapter_type in ("tar1090_http", "tar1090"):
            return Tar1090HttpAdapter(source_id, name, config)
        elif adapter_type in ("readsb_json", "readsb"):
            return ReadsbJsonAdapter(source_id, name, config)
        elif adapter_type in ("sbs_tcp", "sbs", "basestation"):
            return SbsTcpAdapter(source_id, name, config)
        elif adapter_type in ("beast_tcp", "beast"):
            return BeastTcpAdapter(source_id, name, config)
        else:
            logger.warning("Unknown adapter type '%s', falling back to Tar1090HttpAdapter", adapter_type)
            return Tar1090HttpAdapter(source_id, name, config)

    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> List[BaseInputAdapter]:
        adapters = []
        if "sources" in config and isinstance(config["sources"], list):
            for i, src in enumerate(config["sources"]):
                if src.get("enabled", True):
                    source_id = src.get("id", f"source_{i}")
                    name = src.get("name", f"Source {i}")
                    adapter_type = src.get("type", "tar1090_http")
                    adapter = AdapterFactory.create_adapter(source_id, adapter_type, name, src)
                    adapters.append(adapter)

        if not adapters:
            tar1090_url = config.get("tar1090", {}).get("url", "http://localhost/tar1090/data/aircraft.json")
            default_adapter = Tar1090HttpAdapter(
                source_id="default_tar1090",
                name="Local tar1090",
                config={"url": tar1090_url, "priority": 1}
            )
            adapters.append(default_adapter)

        return adapters

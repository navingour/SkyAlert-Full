from typing import List, Dict, Any
from app.models.aircraft import NormalizedAircraft
from app.adapters.base import BaseInputAdapter


class AircraftDeduplicator:

    def deduplicate(
        self,
        telemetry_batch: List[NormalizedAircraft],
        adapters: List[BaseInputAdapter]
    ) -> List[NormalizedAircraft]:

        if not telemetry_batch:
            return []

        priority_map = {adapter.source_id: adapter.priority for adapter in adapters}

        grouped: Dict[str, List[NormalizedAircraft]] = {}
        for item in telemetry_batch:
            hex_code = item.hex
            if hex_code not in grouped:
                grouped[hex_code] = []
            grouped[hex_code].append(item)

        deduplicated: List[NormalizedAircraft] = []

        for hex_code, plane_list in grouped.items():
            if len(plane_list) == 1:
                deduplicated.append(plane_list[0])
                continue

            sorted_planes = sorted(
                plane_list,
                key=lambda p: priority_map.get(p.source_id, 999)
            )

            primary = sorted_planes[0]
            merged_dict = primary.model_dump()

            for secondary in sorted_planes[1:]:
                sec_dict = secondary.model_dump()
                for key, val in sec_dict.items():
                    if val is not None and merged_dict.get(key) is None:
                        merged_dict[key] = val

            deduplicated.append(NormalizedAircraft(**merged_dict))

        return deduplicated

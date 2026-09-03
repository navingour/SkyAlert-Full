from collections.abc import Mapping

from web.services.config_metadata import FIELD_METADATA


class ConfigSchema:

    def build(self, data):

        sections = []

        self.walk(
            data=data,
            sections=sections,
            prefix=""
        )

        return sections

    def walk(self, data, sections, prefix):

        for section_name, section_data in data.items():

            if not isinstance(section_data, Mapping):
                continue

            section = {
                "title": (
                    f"{prefix}.{section_name}"
                    if prefix
                    else section_name
                ),
                "display": section_name.replace(
                    "_",
                    " "
                ).title(),
                "fields": []
            }

            has_child = False

            for key, value in section_data.items():

                if isinstance(value, Mapping):

                    has_child = True

                    self.walk(
                        {key: value},
                        sections,
                        section["title"]
                    )

                    continue

                meta = FIELD_METADATA.get(
                    f"{section['title']}.{key}",
                    {}
                )

                field = {
                    "key": key,
                    "label": meta.get(
                        "label",
                        key.replace("_", " ").title()
                    ),
                    "icon": meta.get(
                        "icon",
                        ""
                    ),
                    "help": meta.get(
                        "help",
                        ""
                    ),
                    "value": value
                }

                if isinstance(value, bool):

                    field["type"] = "bool"

                elif isinstance(value, int):

                    field["type"] = "number"

                elif isinstance(value, list):

                    field["type"] = "list"

                elif isinstance(value, str):

                    field["type"] = meta.get(
                        "type",
                        "text"
                    )

                else:

                    field["type"] = "unknown"

                section["fields"].append(field)

            if section["fields"] or not has_child:

                sections.append(section)


config_schema = ConfigSchema()

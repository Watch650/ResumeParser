# utils/mappings.py

def map_degree_to_id(degree: str) -> int:
    degree = degree.strip().lower()
    if any(k in degree for k in ["trung học", "thpt"]):
        return 1  # high_school
    elif any(k in degree for k in ["trung cấp", "cao đẳng"]):
        return 2  # college
    elif any(k in degree for k in ["đại học", "học viện"]) and not any(k in degree for k in ["thạc sĩ", "tiến sĩ"]):
        return 3  # university
    elif any(k in degree for k in ["thạc sĩ", "tiến sĩ"]):
        return 4  # after_university
    # elif "không yêu cầu" in degree:
    #     return 6  # none
    else:
        return 5  # other

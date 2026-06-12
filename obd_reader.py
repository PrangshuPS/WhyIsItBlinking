from openf1_client import ensure_default_selection, get_current_state, get_current_samples, next_sample, prepare_selection, get_track_catalog, get_driver_catalog


def fetch_data():
    sample = next_sample()
    if sample:
        return sample
    default_state = ensure_default_selection()
    if default_state.get("status") == "ok":
        return next_sample()
    return {}


def get_track_options():
    return get_track_catalog()


def get_driver_options(meeting_key: int):
    return get_driver_catalog(meeting_key)


def select_openf1_source(meeting_key: int, driver_number: int):
    return prepare_selection(meeting_key, driver_number)


def get_openf1_state():
    return get_current_state()


def get_openf1_samples():
    return get_current_samples()
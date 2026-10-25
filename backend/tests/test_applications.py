from tests.conftest import login_headers


def first_job_id(client, headers):
    return client.get("/jobs", headers=headers).json()["jobs"][0]["id"]


def test_full_crud(client, headers):
    jid = first_job_id(client, headers)
    res = client.post("/applications", headers=headers, json={"job_id": jid})
    assert res.status_code == 201 and res.json()["status"] == "Saved"
    aid = res.json()["id"]
    upd = client.patch(f"/applications/{aid}", headers=headers, json={"status": "Applied", "notes": "Referred"})
    assert upd.json()["status"] == "Applied" and upd.json()["applied_date"]
    assert len(client.get("/applications?status=Applied", headers=headers).json()) == 1
    assert client.get("/applications?q=referred", headers=headers).json()
    assert client.delete(f"/applications/{aid}", headers=headers).status_code == 204
    assert client.get("/applications", headers=headers).json() == []


def test_duplicate_and_invalid(client, headers):
    jid = first_job_id(client, headers)
    client.post("/applications", headers=headers, json={"job_id": jid})
    assert client.post("/applications", headers=headers, json={"job_id": jid}).status_code == 409
    assert client.post("/applications", headers=headers, json={"job_id": jid, "status": "Maybe"}).status_code == 422
    assert client.post("/applications", headers=headers, json={"job_id": "000000000000000000000000"}).status_code == 404


def test_users_cannot_touch_each_others_records(client, headers):
    jid = first_job_id(client, headers)
    aid = client.post("/applications", headers=headers, json={"job_id": jid}).json()["id"]
    other = login_headers(client, "b@example.com")
    assert client.get("/applications", headers=other).json() == []
    assert client.patch(f"/applications/{aid}", headers=other, json={"notes": "hack"}).status_code == 404
    assert client.delete(f"/applications/{aid}", headers=other).status_code == 404
    assert len(client.get("/applications", headers=headers).json()) == 1


def test_sorting(client, headers):
    jobs = client.get("/jobs", headers=headers).json()["jobs"]
    for j in jobs[:3]:
        client.post("/applications", headers=headers, json={"job_id": j["id"]})
    names = [a["company"] for a in client.get("/applications?sort=company", headers=headers).json()]
    assert names == sorted(names)

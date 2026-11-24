import os
import json
import urllib.request

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["DATABASE_ID"]

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def fetch_all_pages():
    url = f"https://notion.com{DATABASE_ID}/query"
    pages = []
    has_more = True
    next_cursor = None

    while has_more:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=HEADERS,
            method="POST"
        )
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            pages.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")

    return pages

def build_graph(pages):
    nodes = []
    edges = []
    seen_edges = set()

    for page in pages:
        page_id = page["id"]
        page_url = page["url"]
        props = page["properties"]

        # 1. Buscar automáticamente la propiedad de tipo 'title'
        title = "Sin título"
        for prop_data in props.values():
            if prop_data.get("type") == "title":
                title_list = prop_data.get("title", [])
                if title_list:
                    title = "".join(t.get("plain_text", "") for t in title_list)
                break

        # 2. Obtener categoría (Propiedad Select llamada 'Categoría')
        category = "General"
        cat_prop = props.get("Categoría", {})
        if cat_prop.get("type") == "select" and cat_prop.get("select"):
            category = cat_prop["select"].get("name", "General")

        nodes.append({
            "id": page_id,
            "label": title,
            "group": category,
            "url": page_url
        })

        # 3. Obtener conexiones (Propiedad Relation llamada 'Conexiones')
        rel_prop = props.get("Conexiones", {})
        if rel_prop.get("type") == "relation":
            for rel in rel_prop.get("relation", []):
                target_id = rel["id"]
                # Evitar líneas duplicadas entre A->B y B->A
                edge_pair = tuple(sorted([page_id, target_id]))
                if edge_pair not in seen_edges:
                    seen_edges.add(edge_pair)
                    edges.append({
                        "from": page_id,
                        "to": target_id
                    })

    return {"nodes": nodes, "edges": edges}

if __name__ == "__main__":
    pages = fetch_all_pages()
    graph_data = build_graph(pages)
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(graph_data, f, ensure_ascii=False, indent=2)
    print(f"Grafo actualizado: {len(graph_data['nodes'])} nodos, {len(graph_data['edges'])} conexiones.")

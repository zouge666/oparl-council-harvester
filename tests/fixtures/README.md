# Test fixtures

Made up OParl answers for the tests. They look like the Dresden (Somacos) api,
but the urls use `example.test` so the tests never call a real server.
The papers are made up too, they are not real council papers.

- `system.json`, `bodies.json` - the start of the api
- `papers_page1.json` - first page: good papers, a broken one, one without a title
- `papers_page2.json` - last page: a double paper, a deleted one, a old one,
  a excluded one, swapped coordinates and a bad date
- `papers_empty.json` - a list with no papers in it

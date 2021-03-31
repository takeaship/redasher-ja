import os
import gzip

from tqdm import tqdm
import click
import json

try:
    from redash import models
    from redash.utils import json_dumps
except:
    print "The export script needs to be run from /opt/redash/current."
    exit()


def export_model(model, path="."):
    name = model.__name__
    filename = os.path.join(path, "{}_export.jsonl.gz".format(name.lower()))

    print "Exporting {} into: {}".format(name, filename)

    has_records = True
    query = model.select()
    current_id = 0
    new_id = 0
    records_count = 0
    progress = tqdm(model.select().count(), leave=True)
    header = None

    with gzip.open(filename, 'wb') as fh:
        while has_records:
            results = query.where(model.id > current_id).limit(100).order_by(model.id.asc())
            new_id = current_id

            for row in results.dicts().iterator():
                new_id = row['id']
                fh.write(json_dumps(row))
                fh.write(u"\n")
                records_count += 1
                progress.update()

            if new_id == current_id:
                has_records = False

            current_id = new_id

    progress.close()

    print "Saved {} records.".format(records_count)

    return filename

@click.command()
@click.option('--path', default=".", help='Directory to export into.')
def export(path):
    for model in models.all_models:
        filename = export_model(model, path)

if __name__ == '__main__':
    export()
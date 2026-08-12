/**
 * MoonieX personal Google Drive filing bridge.
 *
 * Deploy: script.google.com -> paste this file -> Services (+) -> add
 * "Drive API" advanced service -> Project Settings -> Script Properties ->
 * add SECRET_TOKEN -> Deploy > New deployment > Web app
 * (Execute as: Me, Who has access: Anyone).
 *
 * All operations are metadata-only (Drive API v3 files.update /
 * files.create with addParents/removeParents) — no file content is ever
 * re-uploaded or copied, so nothing is at risk of being dropped mid-move.
 */

function doPost(e) {
  var secret = PropertiesService.getScriptProperties().getProperty('SECRET_TOKEN');
  var body;
  try {
    body = JSON.parse(e.postData.contents);
  } catch (err) {
    return jsonResponse({ ok: false, error: 'invalid_json' });
  }
  if (!secret || body.token !== secret) {
    return jsonResponse({ ok: false, error: 'unauthorized' });
  }
  try {
    var result;
    switch (body.action) {
      case 'move':
        result = moveFile(body.fileId, body.newParentId);
        break;
      case 'rename':
        result = renameFile(body.fileId, body.newName);
        break;
      case 'trash':
        result = setTrashed(body.fileId, true);
        break;
      case 'untrash':
        result = setTrashed(body.fileId, false);
        break;
      case 'create_folder':
        result = createFolder(body.name, body.parentId);
        break;
      case 'list':
        result = listFolder(body.folderId);
        break;
      case 'create_file':
        result = createTextFile(body.name, body.parentId, body.content);
        break;
      case 'create_doc':
        result = createDoc(body.name, body.parentId, body.content);
        break;
      case 'read_file':
        result = readTextFile(body.fileId);
        break;
      case 'append_log':
        result = appendLog(body.fileId, body.lines);
        break;
      default:
        return jsonResponse({ ok: false, error: 'unknown_action: ' + body.action });
    }
    return jsonResponse({ ok: true, result: result });
  } catch (err) {
    return jsonResponse({ ok: false, error: String(err) });
  }
}

function doGet(e) {
  return jsonResponse({ ok: true, msg: 'gdrive-bridge alive' });
}

function moveFile(fileId, newParentId) {
  var file = Drive.Files.get(fileId, { fields: 'parents,name' });
  // Drive v2 returns parents as objects ({id: ...}); v3 returns plain id
  // strings. This deployment is on v3 (confirmed 2026-08-12 from the live
  // manifest), where the old `p.id` yielded undefined for every parent and
  // removeParents was sent the literal string "undefined" — so a move added
  // the new parent without ever detaching the old one. Handle both shapes.
  var previousParents = (file.parents || []).map(function (p) {
    return (typeof p === 'string') ? p : p.id;
  }).filter(function (id) { return !!id; }).join(',');
  return Drive.Files.update({}, fileId, null, {
    addParents: newParentId,
    removeParents: previousParents,
    fields: 'id,name,parents'
  });
}

function renameFile(fileId, newName) {
  return Drive.Files.update({ name: newName }, fileId, null, { fields: 'id,name' });
}

function setTrashed(fileId, trashed) {
  return Drive.Files.update({ trashed: trashed }, fileId, null, { fields: 'id,name,trashed' });
}

function createFolder(name, parentId) {
  var resource = {
    name: name,
    mimeType: 'application/vnd.google-apps.folder',
    parents: parentId ? [parentId] : []
  };
  return Drive.Files.create(resource, null, { fields: 'id,name,parents' });
}

/**
 * Read-side + log-side actions (added 2026-08-12 for the YT: ILAG per-project
 * logs.txt rule). These deliberately use the built-in DriveApp service rather
 * than the advanced `Drive` service used above: DriveApp's API is stable
 * across Drive API v2/v3, so these keep working regardless of which advanced
 * service version the deployment has enabled.
 */

/** List one folder's direct children (folders first, then files). */
function listFolder(folderId) {
  var folder = DriveApp.getFolderById(folderId);
  var items = [];

  var folders = folder.getFolders();
  while (folders.hasNext()) {
    var sub = folders.next();
    items.push({
      type: 'folder',
      id: sub.getId(),
      name: sub.getName(),
      created: sub.getDateCreated().toISOString(),
      link: 'https://drive.google.com/drive/folders/' + sub.getId()
    });
  }

  var files = folder.getFiles();
  while (files.hasNext()) {
    var file = files.next();
    items.push({
      type: 'file',
      id: file.getId(),
      name: file.getName(),
      mime: file.getMimeType(),
      size: file.getSize(),
      created: file.getDateCreated().toISOString(),
      modified: file.getLastUpdated().toISOString(),
      link: 'https://drive.google.com/file/d/' + file.getId() + '/view'
    });
  }

  return { folderId: folderId, name: folder.getName(), count: items.length, items: items };
}

/** Create a plain-text file (this is how logs.txt gets born). */
function createTextFile(name, parentId, content) {
  var parent = DriveApp.getFolderById(parentId);
  var file = parent.createFile(name, content || '', MimeType.PLAIN_TEXT);
  return {
    id: file.getId(),
    name: file.getName(),
    link: 'https://drive.google.com/file/d/' + file.getId() + '/view'
  };
}

/**
 * Create an empty Google Doc inside parentId (e.g. the StoryBoard doc).
 *
 * Uses Drive.Files.create with the Docs mimeType rather than
 * DocumentApp.create: DocumentApp needs the auth/documents scope, which this
 * deployment has never been granted. Deploying does not re-prompt for new
 * scopes (Apps Script asks at run time, not at deploy time), so the
 * DocumentApp version failed at runtime on 2026-08-12 with "คุณไม่ได้รับ
 * อนุญาตให้เรียกใช้ DocumentApp.create". Creating the doc as a Drive file
 * needs no scope the bridge does not already hold.
 */
function createDoc(name, parentId, content) {
  var resource = {
    name: name,
    mimeType: 'application/vnd.google-apps.document',
    parents: parentId ? [parentId] : []
  };
  // Uploading an HTML blob against the Docs mimeType makes Drive convert it on
  // the way in, so the doc arrives with its content already formatted — no
  // second call and no DocumentApp scope to write the body.
  var media = content ? Utilities.newBlob(content, 'text/html', name + '.html') : null;
  var created = Drive.Files.create(resource, media, { fields: 'id,name' });
  return {
    id: created.id,
    name: created.name,
    link: 'https://docs.google.com/document/d/' + created.id + '/edit'
  };
}

/** Read a plain-text file back (so an agent can reconcile against logs.txt). */
function readTextFile(fileId) {
  var file = DriveApp.getFileById(fileId);
  return {
    id: fileId,
    name: file.getName(),
    content: file.getBlob().getDataAsString('UTF-8')
  };
}

/**
 * Append lines to a text file. Append-only by construction: existing content is
 * read, new lines are added after it, nothing is ever removed or rewritten.
 * ScriptLock serialises concurrent agents so two appends can't clobber each other.
 */
function appendLog(fileId, lines) {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(20000)) {
    throw new Error('append_log: could not acquire lock within 20s');
  }
  try {
    var file = DriveApp.getFileById(fileId);
    var current = file.getBlob().getDataAsString('UTF-8');
    var incoming = (Array.isArray(lines) ? lines : [lines]).join('\n');

    if (current.length > 0 && current.charAt(current.length - 1) !== '\n') {
      current += '\n';
    }
    var next = current + incoming + '\n';
    file.setContent(next);

    return {
      id: fileId,
      name: file.getName(),
      appended: Array.isArray(lines) ? lines.length : 1,
      bytes: next.length
    };
  } finally {
    lock.releaseLock();
  }
}

function jsonResponse(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

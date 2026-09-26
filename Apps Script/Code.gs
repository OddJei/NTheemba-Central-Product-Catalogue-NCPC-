/**
 * Ntheemba Central Product Catalogue (NCPC)
 * Standalone Google Apps Script catalogue application.
 *
 * This project deliberately contains no TradeFlow or Ntheemba Bot integration.
 * It creates and operates its own Google Sheets database, review queues,
 * research evidence, resumable imports, barcode verification and releases.
 */

var NCPC_APP = {
  name: 'Ntheemba Central Product Catalogue',
  shortName: 'NCPC',
  version: '2.0.0',
  databaseProperty: 'NCPC_DATABASE_SPREADSHEET_ID',
  schemaVersion: 'ncpc-2.0',
  supportedResearchSchema: 'apps-script-research-import-v1',
  defaultMarketCode: 'ZM'
};

// Public, read-only response contract for downstream identity matching. Keep
// this distinct from the NCPC database schema and from admin UI responses.
var NCPC_CANDIDATE_SEARCH_CONTRACT_VERSION = 'ncpc-candidate-search-v1';

var NCPC_TABLES = {
  CatalogueDomains: [
    'id','name','description','status','createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  Categories: [
    'id','catalogueDomainId','parentCategoryId','name','description','status',
    'createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  Organizations: [
    'id','legalName','tradingName','countryCode','websiteUrl','description',
    'verificationStatus','status','createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  OrganizationRoles: [
    'id','organizationId','roleType','territoryCode','effectiveFrom','effectiveTo',
    'verificationStatus','status','createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  Brands: [
    'id','name','description','verificationStatus','status',
    'createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  BrandOrganizationRelationships: [
    'id','brandId','organizationId','relationshipType','territoryCode','sourceId',
    'verificationStatus','status','createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  Products: [
    'id','catalogueDomainId','categoryId','brandId','canonicalName','description','productType',
    'qualityTier','verificationStatus','publicationStatus','status',
    'createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  ProductVariants: [
    'id','productId','variantName','sizeValue','sizeUnit','salesUnit','packagingType','inventoryType',
    'verificationStatus','publicationStatus','status',
    'createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  Identifiers: [
    'id','variantId','identifierType','identifierValue','isPrimary','sourceId',
    'verificationStatus','status','createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  ProductAliases: [
    'id','productId','variantId','alias','languageCode','aliasType','status',
    'createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  DigitalAssets: [
    'id','productId','variantId','assetType','sourceUrl','storageUrl','caption','sourceId',
    'verificationStatus','status','createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  ProductOrganizationRelationships: [
    'id','productId','variantId','organizationId','relationshipType','territoryCode','sourceId',
    'verificationStatus','status','createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  InformationSources: [
    'id','externalSourceId','title','url','sourceType','authority','organizationId',
    'documentDate','accessedAt','notes','status',
    'createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  CatalogueEvidence: [
    'id','productId','variantId','sourceId','claimType','claimValue','evidenceTier','confidence',
    'verificationStatus','reviewNotes','status',
    'createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  ProductCandidates: [
    'id','originType','originReference','rawName','rawPayload','proposedProductId','status',
    'reviewNotes','submittedBy','submittedAt','reviewedBy','reviewedAt',
    'createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  ReviewQueue: [
    'id','queueType','entityType','entityId','priority','reason','status','assignedTo','dueAt',
    'resolution','resolutionNotes','createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  BarcodeVerificationQueue: [
    'id','variantId','identifierValue','identifierType','submittedBy','submissionSource','photoUrl',
    'sourceId','status','verificationNotes','verifiedBy','verifiedAt',
    'createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  ImportJobs: [
    'id','manifestId','schemaVersion','fileName','marketCode','totalItems','queuedItems','processedItems',
    'createdItems','mergedItems','candidateItems','skippedItems','failedItems','status','currentStage',
    'progressPercent','errorSummary','startedAt','completedAt',
    'createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  ImportItems: [
    'id','importJobId','itemIndex','externalKey','rawPayload','normalizedName','evidenceTier','status',
    'action','entityId','errorMessage','createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  CatalogueReleases: [
    'id','releaseName','releaseVersion','description','status','productCount','variantCount',
    'publishedAt','publishedBy','createdAt','updatedAt','createdBy','updatedBy','version'
  ],
  ReleaseItems: [
    'id','releaseId','entityType','entityId','entityVersion','createdAt','createdBy'
  ],
  AuditEvents: [
    'id','timestamp','userEmail','action','entityType','entityId','oldValue','newValue','notes'
  ],
  SystemSettings: [
    'key','value','description','updatedAt'
  ],
  Sequences: [
    'entityType','lastNumber','updatedAt'
  ]
};

var NCPC_PREFIXES = {
  CatalogueDomains: 'DOM',
  Categories: 'CAT',
  Organizations: 'ORG',
  OrganizationRoles: 'ORL',
  Brands: 'BRD',
  BrandOrganizationRelationships: 'BOR',
  Products: 'PRD',
  ProductVariants: 'VAR',
  Identifiers: 'IDN',
  ProductAliases: 'ALS',
  DigitalAssets: 'AST',
  ProductOrganizationRelationships: 'POR',
  InformationSources: 'SRC',
  CatalogueEvidence: 'EVD',
  ProductCandidates: 'CAN',
  ReviewQueue: 'REV',
  BarcodeVerificationQueue: 'BVQ',
  ImportJobs: 'IMP',
  ImportItems: 'ITM',
  CatalogueReleases: 'REL',
  ReleaseItems: 'RLI',
  AuditEvents: 'AUD'
};

var NCPC_VERSIONED_TABLES = [
  'CatalogueDomains','Categories','Organizations','OrganizationRoles','Brands',
  'BrandOrganizationRelationships','Products','ProductVariants','Identifiers',
  'ProductAliases','DigitalAssets','ProductOrganizationRelationships','InformationSources',
  'CatalogueEvidence','ProductCandidates','ReviewQueue','BarcodeVerificationQueue',
  'ImportJobs','ImportItems','CatalogueReleases'
];

var NCPC_ALLOWED_ORGANIZATION_ROLES = [
  'brand_owner','manufacturer','contract_manufacturer','bottler','packer','importer','exporter',
  'distributor','authorized_distributor','wholesaler','retailer','supplier','licensor','licensee',
  'standards_body','regulatory_authority','data_provider'
];

var NCPC_ALLOWED_RELATIONSHIPS = [
  'brand_owned_by','manufactured_by','contract_manufactured_by','bottled_by','packed_by',
  'imported_by','distributed_by','authorized_distributor','supplied_by','licensed_by',
  'marketed_by','verified_by','data_provided_by'
];

var NCPC_PROTECTED_TRADEFLOW_FIELDS = {
  sellingprice: true, price: true, extractedprice: true, cost: true, costprice: true, unitcost: true,
  stock: true, currentstock: true, openingstock: true, availablequantity: true,
  quantityremaining: true, quantityonhand: true, maxstock: true, reorderlevel: true,
  supplier: true, supplierid: true, suppliername: true, preferredsupplier: true,
  batches: true, inventorybatches: true, stockentries: true, stockadjustments: true,
  revenue: true, expenses: true, sales: true, profit: true, profitmargin: true,
  margin: true, inventoryvalue: true
};

/* -------------------------------------------------------------------------- */
/* Entry points                                                               */
/* -------------------------------------------------------------------------- */

function onOpen() {
  try {
    SpreadsheetApp.getUi()
      .createMenu('NCPC')
      .addItem('Initialize NCPC Database', 'initializeNcpcSystem')
      .addItem('Open NCPC Web App', 'showNcpcWebAppHelp')
      .addSeparator()
      .addItem('Create Catalogue Release', 'createReleaseFromMenu_')
      .addItem('Export Published Catalogue', 'exportPublishedCatalogueFromMenu_')
      .addToUi();
  } catch (e) {
    Logger.log(e.message);
  }
}

function showNcpcWebAppHelp() {
  SpreadsheetApp.getUi().showModalDialog(
    HtmlService.createHtmlOutput(
      '<div style="font:14px Arial;padding:18px">' +
      '<h3>Ntheemba Central Product Catalogue</h3>' +
      '<p>Deploy this Apps Script project as a web app and open the deployment URL.</p>' +
      '<p>Run <b>initializeNcpcSystem</b> once before first use.</p>' +
      '</div>'
    ).setWidth(430).setHeight(220),
    NCPC_APP.name
  );
}

function doGet() {
  var params = arguments[0] && arguments[0].parameter || {};
  // `api` is retained for the original TradeFlow-facing contract; `action`
  // remains the current NCPC web-app spelling.
  var action = String(params.action || params.api || '').toLowerCase();
  if (action) return handleNcpcReadApi_(arguments[0], action);
  return HtmlService.createTemplateFromFile('Index')
    .evaluate()
    .setTitle(NCPC_APP.name)
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function initializeNcpcSystem() {
  try {
    var properties = PropertiesService.getScriptProperties();
    var ss = getNcpcDatabase_();
    var initializedSchema = properties.getProperty('NCPC_INITIALIZED_SCHEMA_VERSION');
    if (initializedSchema === NCPC_APP.schemaVersion && ss.getSheetByName('Products')) {
      return ncpcOk_({
        spreadsheetId: ss.getId(),
        spreadsheetName: ss.getName(),
        spreadsheetUrl: ss.getUrl(),
        tableCount: Object.keys(NCPC_TABLES).length,
        schemaVersion: NCPC_APP.schemaVersion,
        alreadyInitialized: true
      }, 'NCPC database is ready');
    }
    Object.keys(NCPC_TABLES).forEach(function (tableName) {
      ensureNcpcSheet_(ss, tableName);
    });

    seedSetting_('applicationName', NCPC_APP.name, 'Application name');
    seedSetting_('applicationVersion', NCPC_APP.version, 'Application version');
    seedSetting_('schemaVersion', NCPC_APP.schemaVersion, 'Database schema version');
    seedSetting_('catalogueVersion', '1', 'Monotonic catalogue data version');
    seedSetting_('defaultMarketCode', NCPC_APP.defaultMarketCode, 'Default catalogue market');
    seedSetting_('publicationRequiresReview', 'true', 'Products must pass review before publication');
    seedSetting_('defaultImportBatchSize', '25', 'Default number of import items processed per call');

    if (!findByNormalizedField_('CatalogueDomains', 'name', 'Retail & Grocery')) {
      createRecord_('CatalogueDomains', {
        name: 'Retail & Grocery',
        description: 'Retail grocery, convenience and general merchandise',
        status: 'active'
      }, 'SYSTEM_INITIALIZATION');
    }

    properties.setProperty('NCPC_INITIALIZED_SCHEMA_VERSION', NCPC_APP.schemaVersion);
    writeAuditEvent_('INITIALIZE_SYSTEM', 'System', 'NCPC', null, {
      spreadsheetId: ss.getId(),
      spreadsheetName: ss.getName(),
      schemaVersion: NCPC_APP.schemaVersion
    }, 'Fresh NCPC database structure initialized');

    return ncpcOk_({
      spreadsheetId: ss.getId(),
      spreadsheetName: ss.getName(),
      spreadsheetUrl: ss.getUrl(),
      tableCount: Object.keys(NCPC_TABLES).length,
      schemaVersion: NCPC_APP.schemaVersion
    }, 'NCPC database initialized');
  } catch (e) {
    return ncpcFail_(e.message, 'INITIALIZATION_FAILED');
  }
}

function getNcpcBootstrap() {
  try {
    initializeNcpcSystem();
    setSetting_('catalogueVersion', String(getCatalogueVersion_()), 'Monotonic catalogue data version');
    return ncpcOk_({
      application: NCPC_APP,
      database: getDatabaseInfo_(),
      integration: getNcpcIntegrationInfo_(),
      dashboard: getNcpcDashboard().data,
      referenceData: getNcpcReferenceData().data,
      settings: rows_('SystemSettings'),
      enums: {
        organizationRoles: NCPC_ALLOWED_ORGANIZATION_ROLES,
        organizationRelationships: NCPC_ALLOWED_RELATIONSHIPS,
        verificationStatuses: ['unverified','reviewed','verified','disputed'],
        publicationStatuses: ['draft','in_review','published','withdrawn','rejected'],
        evidenceTiers: ['official_exact','institution_linked_family','market_pack_candidate','shop_seed','physical_scan'],
        priorities: ['low','normal','high','critical']
      }
    }, 'NCPC application loaded');
  } catch (e) {
    return ncpcFail_(e.message, 'BOOTSTRAP_FAILED');
  }
}

/* -------------------------------------------------------------------------- */
/* Database and sheet helpers                                                 */
/* -------------------------------------------------------------------------- */

function getNcpcDatabase_() {
  var properties = PropertiesService.getScriptProperties();
  var databaseId = properties.getProperty(NCPC_APP.databaseProperty);
  if (databaseId) {
    try {
      return SpreadsheetApp.openById(databaseId);
    } catch (e) {
      properties.deleteProperty(NCPC_APP.databaseProperty);
    }
  }

  var activeSpreadsheet = null;
  try {
    activeSpreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  } catch (ignore) {}

  var ss = activeSpreadsheet || SpreadsheetApp.create(NCPC_APP.name + ' Database');
  properties.setProperty(NCPC_APP.databaseProperty, ss.getId());
  return ss;
}

function getDatabaseInfo_() {
  var ss = getNcpcDatabase_();
  return {
    id: ss.getId(),
    name: ss.getName(),
    url: ss.getUrl(),
    timezone: ss.getSpreadsheetTimeZone()
  };
}

function ensureNcpcSheet_(ss, tableName) {
  if (!NCPC_TABLES[tableName]) throw new Error('Unknown NCPC table: ' + tableName);
  var headers = NCPC_TABLES[tableName];
  var sheet = ss.getSheetByName(tableName);
  if (!sheet) sheet = ss.insertSheet(tableName);

  var existingHeaders = [];
  if (sheet.getLastRow() > 0) {
    existingHeaders = sheet.getRange(1, 1, 1, Math.max(sheet.getLastColumn(), headers.length)).getValues()[0];
  }

  if (sheet.getLastRow() === 0 || existingHeaders.filter(String).length === 0) {
    sheet.clear();
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  } else {
    var current = existingHeaders.slice(0, headers.length).map(String);
    if (current.join('|') !== headers.join('|')) {
      throw new Error(
        'The sheet "' + tableName + '" already exists with incompatible columns. ' +
        'Because NCPC has not been initialized before, rename or remove that sheet and initialize again.'
      );
    }
  }

  styleNcpcSheet_(sheet, headers.length);
  return sheet;
}

function styleNcpcSheet_(sheet, columnCount) {
  sheet.setFrozenRows(1);
  sheet.getRange(1, 1, 1, columnCount)
    .setBackground('#071A33')
    .setFontColor('#FFFFFF')
    .setFontWeight('bold')
    .setWrap(true);
  sheet.setRowHeight(1, 32);
  for (var column = 1; column <= columnCount; column++) {
    if (sheet.getColumnWidth(column) < 110) sheet.setColumnWidth(column, 130);
  }
}

function ncpcSheet_(tableName) {
  return ensureNcpcSheet_(getNcpcDatabase_(), tableName);
}

function rows_(tableName) {
  var sheet = ncpcSheet_(tableName);
  var values = sheet.getDataRange().getValues();
  var headers = NCPC_TABLES[tableName];
  if (values.length < 2) return [];

  return values.slice(1).filter(function (row) {
    return row.some(function (value) { return value !== ''; });
  }).map(function (row) {
    var record = {};
    headers.forEach(function (header, index) { record[header] = row[index]; });
    return record;
  });
}

function rowValues_(tableName, record) {
  return NCPC_TABLES[tableName].map(function (header) {
    var value = record[header];
    if (value === undefined || value === null) return '';
    return value;
  });
}

function getRecord_(tableName, id) {
  return rows_(tableName).filter(function (record) { return String(record.id) === String(id); })[0] || null;
}

function getRowNumber_(tableName, id) {
  var sheet = ncpcSheet_(tableName);
  var headers = NCPC_TABLES[tableName];
  var idColumn = headers.indexOf('id') + 1;
  if (!idColumn || sheet.getLastRow() < 2) return -1;
  var finder = sheet.getRange(2, idColumn, sheet.getLastRow() - 1, 1)
    .createTextFinder(String(id))
    .matchEntireCell(true)
    .findNext();
  return finder ? finder.getRow() : -1;
}

function appendRows_(tableName, records) {
  if (!records || !records.length) return;
  var sheet = ncpcSheet_(tableName);
  var values = records.map(function (record) { return rowValues_(tableName, record); });
  sheet.getRange(sheet.getLastRow() + 1, 1, values.length, NCPC_TABLES[tableName].length).setValues(values);
}

function replaceRecord_(tableName, id, record) {
  var rowNumber = getRowNumber_(tableName, id);
  if (rowNumber < 2) throw new Error(tableName + ' record not found: ' + id);
  ncpcSheet_(tableName)
    .getRange(rowNumber, 1, 1, NCPC_TABLES[tableName].length)
    .setValues([rowValues_(tableName, record)]);
}

function normalizeText_(value) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/&/g, ' and ')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function findByNormalizedField_(tableName, fieldName, value) {
  var normalized = normalizeText_(value);
  if (!normalized) return null;
  return rows_(tableName).filter(function (record) {
    return normalizeText_(record[fieldName]) === normalized;
  })[0] || null;
}

function nowIso_() {
  return new Date().toISOString();
}

function currentUser_() {
  try {
    return Session.getActiveUser().getEmail() || Session.getEffectiveUser().getEmail() || 'unknown-user';
  } catch (e) {
    return 'unknown-user';
  }
}

function nextSequence_(entityType) {
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var properties = PropertiesService.getScriptProperties();
    var key = 'NCPC_SEQUENCE_' + entityType;
    var current = Number(properties.getProperty(key) || 0);
    if (!current) {
      var existing = rows_('Sequences').filter(function (record) {
        return record.entityType === entityType;
      })[0];
      current = Number(existing ? existing.lastNumber : 0);
      if (NCPC_TABLES[entityType] && NCPC_TABLES[entityType].indexOf('id') >= 0) {
        var prefix = NCPC_PREFIXES[entityType] || '';
        var actualMaximum = rows_(entityType).reduce(function (maximum, record) {
          var match = String(record.id || '').match(new RegExp('^' + prefix + '-(\\d+)$'));
          return match ? Math.max(maximum, Number(match[1])) : maximum;
        }, 0);
        current = Math.max(current, actualMaximum);
      }
    }
    var nextNumber = current + 1;
    properties.setProperty(key, String(nextNumber));
    if (nextNumber === 1 || nextNumber % 25 === 0) mirrorSequence_(entityType, nextNumber);
    return nextNumber;
  } finally {
    lock.releaseLock();
  }
}

function mirrorSequence_(entityType, lastNumber) {
  var sheet = ncpcSheet_('Sequences');
  var records = rows_('Sequences');
  var existing = records.filter(function (record) { return record.entityType === entityType; })[0];
  var updatedAt = nowIso_();
  if (existing && records.length) {
    var match = sheet.getRange(2, 1, records.length, 1)
      .createTextFinder(entityType).matchEntireCell(true).findNext();
    if (match) {
      sheet.getRange(match.getRow(), 1, 1, 3).setValues([[entityType, lastNumber, updatedAt]]);
      return;
    }
  }
  appendRows_('Sequences', [{ entityType: entityType, lastNumber: lastNumber, updatedAt: updatedAt }]);
}

function nextId_(tableName) {
  var prefix = NCPC_PREFIXES[tableName];
  if (!prefix) throw new Error('No ID prefix configured for ' + tableName);
  return prefix + '-' + Utilities.formatString('%06d', nextSequence_(tableName));
}

function getCatalogueVersion_() {
  var properties = PropertiesService.getScriptProperties();
  var value = properties.getProperty('NCPC_CATALOGUE_VERSION');
  if (value !== null) return Number(value || 1);
  var setting = rows_('SystemSettings').filter(function (row) { return row.key === 'catalogueVersion'; })[0];
  var version = Number(setting ? setting.value : 1);
  properties.setProperty('NCPC_CATALOGUE_VERSION', String(version));
  return version;
}

function bumpCatalogueVersion_() {
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var properties = PropertiesService.getScriptProperties();
    var next = Number(properties.getProperty('NCPC_CATALOGUE_VERSION') || 1) + 1;
    properties.setProperty('NCPC_CATALOGUE_VERSION', String(next));
    return next;
  } finally {
    lock.releaseLock();
  }
}

function seedSetting_(key, value, description) {
  var existing = rows_('SystemSettings').filter(function (record) { return record.key === key; })[0];
  if (!existing) setSetting_(key, value, description);
}

function setSetting_(key, value, description) {
  if (key === 'catalogueVersion') {
    PropertiesService.getScriptProperties().setProperty('NCPC_CATALOGUE_VERSION', String(value));
  }
  var sheet = ncpcSheet_('SystemSettings');
  var records = rows_('SystemSettings');
  var existing = records.filter(function (record) { return record.key === key; })[0];
  var updatedAt = nowIso_();
  if (existing) {
    var rowNumber = sheet.getRange(2, 1, records.length, 1)
      .createTextFinder(key).matchEntireCell(true).findNext().getRow();
    sheet.getRange(rowNumber, 1, 1, 4).setValues([[key, String(value), description || existing.description, updatedAt]]);
  } else {
    appendRows_('SystemSettings', [{ key: key, value: String(value), description: description || '', updatedAt: updatedAt }]);
  }
}

function getSettingValue_(key, fallback) {
  var setting = rows_('SystemSettings').filter(function (record) { return record.key === key; })[0];
  return setting ? setting.value : fallback;
}

/* -------------------------------------------------------------------------- */
/* Generic records                                                            */
/* -------------------------------------------------------------------------- */

function prepareRecord_(tableName, data, existing) {
  var now = nowIso_();
  var user = currentUser_();
  var record = {};
  NCPC_TABLES[tableName].forEach(function (header) {
    if (data[header] !== undefined) record[header] = data[header];
    else if (existing && existing[header] !== undefined) record[header] = existing[header];
    else record[header] = '';
  });

  if (NCPC_TABLES[tableName].indexOf('id') >= 0 && !record.id) record.id = nextId_(tableName);
  if (NCPC_TABLES[tableName].indexOf('createdAt') >= 0 && !record.createdAt) record.createdAt = now;
  if (NCPC_TABLES[tableName].indexOf('updatedAt') >= 0) record.updatedAt = now;
  if (NCPC_TABLES[tableName].indexOf('createdBy') >= 0 && !record.createdBy) record.createdBy = user;
  if (NCPC_TABLES[tableName].indexOf('updatedBy') >= 0) record.updatedBy = user;
  if (NCPC_TABLES[tableName].indexOf('version') >= 0) record.version = bumpCatalogueVersion_();
  if (NCPC_TABLES[tableName].indexOf('status') >= 0 && !record.status) record.status = 'active';
  return record;
}

function createRecord_(tableName, data, auditAction) {
  if (!NCPC_TABLES[tableName]) throw new Error('Unknown table: ' + tableName);
  var record = prepareRecord_(tableName, data || {}, null);
  appendRows_(tableName, [record]);
  if (String(auditAction || '').indexOf('IMPORT_') !== 0) {
    writeAuditEvent_(auditAction || 'CREATE_RECORD', tableName, record.id || record.key, null, record, 'Record created');
  }
  return record;
}

function updateRecord_(tableName, id, changes, auditAction) {
  var existing = getRecord_(tableName, id);
  if (!existing) throw new Error(tableName + ' record not found: ' + id);
  var updated = prepareRecord_(tableName, changes || {}, existing);
  updated.id = existing.id;
  replaceRecord_(tableName, id, updated);
  if (String(auditAction || '').indexOf('IMPORT_') !== 0 &&
      String(auditAction || '').indexOf('PROCESS_IMPORT_') !== 0 &&
      String(auditAction || '').indexOf('COMPLETE_IMPORT_') !== 0) {
    writeAuditEvent_(auditAction || 'UPDATE_RECORD', tableName, id, existing, updated, 'Record updated');
  }
  return updated;
}

function listNcpcRecords(tableName, filters) {
  try {
    initializeNcpcSystem();
    if (!NCPC_TABLES[tableName]) return ncpcFail_('Unknown table: ' + tableName, 'UNKNOWN_TABLE');
    var records = rows_(tableName);
    filters = filters || {};
    Object.keys(filters).forEach(function (key) {
      if (filters[key] === '' || filters[key] === null || filters[key] === undefined) return;
      records = records.filter(function (record) { return String(record[key]) === String(filters[key]); });
    });
    return ncpcOk_(records, tableName + ' retrieved');
  } catch (e) {
    return ncpcFail_(e.message, 'LIST_FAILED');
  }
}

function createNcpcRecord(tableName, data) {
  try {
    initializeNcpcSystem();
    validateRecord_(tableName, data || {});
    return ncpcOk_(createRecord_(tableName, data, 'CREATE_' + tableName.toUpperCase()), 'Record created');
  } catch (e) {
    return ncpcFail_(e.message, 'CREATE_FAILED');
  }
}

function updateNcpcRecord(tableName, id, changes) {
  try {
    initializeNcpcSystem();
    return ncpcOk_(updateRecord_(tableName, id, changes, 'UPDATE_' + tableName.toUpperCase()), 'Record updated');
  } catch (e) {
    return ncpcFail_(e.message, 'UPDATE_FAILED');
  }
}

function validateRecord_(tableName, data) {
  var required = {
    CatalogueDomains: ['name'],
    Categories: ['catalogueDomainId','name'],
    Organizations: ['legalName'],
    OrganizationRoles: ['organizationId','roleType'],
    Brands: ['name'],
    Products: ['catalogueDomainId','categoryId','canonicalName'],
    ProductVariants: ['productId','variantName'],
    Identifiers: ['variantId','identifierValue'],
    InformationSources: ['title']
  }[tableName] || [];
  required.forEach(function (field) {
    if (!String(data[field] || '').trim()) throw new Error(field + ' is required for ' + tableName);
  });
}

/* -------------------------------------------------------------------------- */
/* Dashboard and reference data                                               */
/* -------------------------------------------------------------------------- */

function getNcpcDashboard() {
  try {
    initializeNcpcSystem();
    var products = rows_('Products');
    var variants = rows_('ProductVariants');
    var identifiers = rows_('Identifiers');
    var review = rows_('ReviewQueue');
    var barcodeQueue = rows_('BarcodeVerificationQueue');
    var jobs = rows_('ImportJobs');
    var evidence = rows_('CatalogueEvidence');

    return ncpcOk_({
      metrics: {
        products: products.length,
        publishedProducts: products.filter(function (row) { return row.publicationStatus === 'published'; }).length,
        draftProducts: products.filter(function (row) { return row.publicationStatus !== 'published'; }).length,
        variants: variants.length,
        identifiers: identifiers.length,
        organizations: rows_('Organizations').length,
        brands: rows_('Brands').length,
        sources: rows_('InformationSources').length,
        evidenceRecords: evidence.length,
        pendingReviews: review.filter(function (row) { return row.status === 'pending' || row.status === 'in_progress'; }).length,
        pendingBarcodes: barcodeQueue.filter(function (row) { return row.status === 'pending'; }).length,
        activeImports: jobs.filter(function (row) { return ['receiving','queued','processing','paused'].indexOf(row.status) >= 0; }).length,
        catalogueVersion: getCatalogueVersion_()
      },
      qualityTiers: countBy_(products, 'qualityTier'),
      publicationStatuses: countBy_(products, 'publicationStatus'),
      reviewTypes: countBy_(review.filter(function (row) { return row.status === 'pending'; }), 'queueType'),
      recentProducts: products.slice(-8).reverse(),
      recentImports: jobs.slice(-8).reverse(),
      recentAudit: rows_('AuditEvents').slice(-10).reverse()
    }, 'Dashboard retrieved');
  } catch (e) {
    return ncpcFail_(e.message, 'DASHBOARD_FAILED');
  }
}

function getNcpcReferenceData() {
  try {
    initializeNcpcSystem();
    return ncpcOk_({
      catalogueDomains: rows_('CatalogueDomains').filter(activeRecord_),
      categories: rows_('Categories').filter(activeRecord_),
      organizations: rows_('Organizations').filter(activeRecord_),
      organizationRoles: rows_('OrganizationRoles').filter(activeRecord_),
      brands: rows_('Brands').filter(activeRecord_),
      informationSources: rows_('InformationSources').filter(activeRecord_)
    }, 'Reference data retrieved');
  } catch (e) {
    return ncpcFail_(e.message, 'REFERENCE_FAILED');
  }
}

function activeRecord_(record) {
  return !record.status || record.status === 'active';
}

function countBy_(records, field) {
  var counts = {};
  records.forEach(function (record) {
    var key = String(record[field] || 'unspecified');
    counts[key] = (counts[key] || 0) + 1;
  });
  return counts;
}

/* -------------------------------------------------------------------------- */
/* Catalogue search and product management                                    */
/* -------------------------------------------------------------------------- */

function searchNcpcCatalogue(query, filters, page, pageSize) {
  try {
    initializeNcpcSystem();
    query = normalizeText_(query);
    filters = filters || {};
    page = Math.max(1, Number(page || 1));
    pageSize = Math.min(100, Math.max(10, Number(pageSize || 25)));

    var domains = indexBy_(rows_('CatalogueDomains'), 'id');
    var categories = indexBy_(rows_('Categories'), 'id');
    var brands = indexBy_(rows_('Brands'), 'id');
    var aliasesByProduct = groupBy_(rows_('ProductAliases').filter(activeRecord_), 'productId');
    var variantsByProduct = groupBy_(rows_('ProductVariants').filter(activeRecord_), 'productId');
    var identifiersByVariant = groupBy_(rows_('Identifiers').filter(activeRecord_), 'variantId');

    var products = rows_('Products').filter(function (product) {
      if (filters.catalogueDomainId && product.catalogueDomainId !== filters.catalogueDomainId) return false;
      if (filters.categoryId && product.categoryId !== filters.categoryId) return false;
      if (filters.brandId && product.brandId !== filters.brandId) return false;
      if (filters.verificationStatus && product.verificationStatus !== filters.verificationStatus) return false;
      if (filters.publicationStatus && product.publicationStatus !== filters.publicationStatus) return false;
      if (filters.qualityTier && product.qualityTier !== filters.qualityTier) return false;
      if (filters.status && product.status !== filters.status) return false;
      if (!query) return true;

      var variants = variantsByProduct[product.id] || [];
      var identifiers = [];
      variants.forEach(function (variant) {
        identifiers = identifiers.concat(identifiersByVariant[variant.id] || []);
      });
      var searchText = [
        product.canonicalName,
        product.description,
        brands[product.brandId] ? brands[product.brandId].name : '',
        categories[product.categoryId] ? categories[product.categoryId].name : '',
        domains[product.catalogueDomainId] ? domains[product.catalogueDomainId].name : ''
      ].concat((aliasesByProduct[product.id] || []).map(function (row) { return row.alias; }))
        .concat(variants.map(function (row) { return row.variantName; }))
        .concat(identifiers.map(function (row) { return row.identifierValue; }))
        .join(' ');
      return normalizeText_(searchText).indexOf(query) >= 0;
    });

    products.sort(function (a, b) {
      return String(b.updatedAt || '').localeCompare(String(a.updatedAt || ''));
    });

    var total = products.length;
    var start = (page - 1) * pageSize;
    var result = products.slice(start, start + pageSize).map(function (product) {
      var variants = variantsByProduct[product.id] || [];
      var identifierCount = variants.reduce(function (sum, variant) {
        return sum + (identifiersByVariant[variant.id] || []).length;
      }, 0);
      return Object.assign({}, product, {
        domainName: domains[product.catalogueDomainId] ? domains[product.catalogueDomainId].name : '',
        categoryName: categories[product.categoryId] ? categories[product.categoryId].name : '',
        brandName: brands[product.brandId] ? brands[product.brandId].name : '',
        variantCount: variants.length,
        identifierCount: identifierCount,
        aliasCount: (aliasesByProduct[product.id] || []).length
      });
    });

    return ncpcOk_({ records: result, total: total, page: page, pageSize: pageSize }, 'Catalogue search completed');
  } catch (e) {
    return ncpcFail_(e.message, 'SEARCH_FAILED');
  }
}

function getNcpcProduct(productId) {
  try {
    initializeNcpcSystem();
    var product = getRecord_('Products', productId);
    if (!product) return ncpcFail_('Product not found', 'PRODUCT_NOT_FOUND');

    var variants = rows_('ProductVariants').filter(function (row) { return row.productId === productId; });
    var variantIds = variants.map(function (row) { return row.id; });
    var identifiers = rows_('Identifiers').filter(function (row) { return variantIds.indexOf(row.variantId) >= 0; });
    var assets = rows_('DigitalAssets').filter(function (row) { return row.productId === productId; });
    var aliases = rows_('ProductAliases').filter(function (row) { return row.productId === productId; });
    var relationships = rows_('ProductOrganizationRelationships').filter(function (row) { return row.productId === productId; });
    var evidence = rows_('CatalogueEvidence').filter(function (row) { return row.productId === productId; });
    var organizations = indexBy_(rows_('Organizations'), 'id');
    var sources = indexBy_(rows_('InformationSources'), 'id');

    variants = variants.map(function (variant) {
      return Object.assign({}, variant, {
        identifiers: identifiers.filter(function (row) { return row.variantId === variant.id; }),
        digitalAssets: assets.filter(function (row) { return row.variantId === variant.id; })
      });
    });

    relationships = relationships.map(function (relationship) {
      return Object.assign({}, relationship, {
        organizationName: organizations[relationship.organizationId]
          ? organizations[relationship.organizationId].tradingName || organizations[relationship.organizationId].legalName
          : '',
        sourceTitle: sources[relationship.sourceId] ? sources[relationship.sourceId].title : ''
      });
    });

    evidence = evidence.map(function (item) {
      return Object.assign({}, item, {
        sourceTitle: sources[item.sourceId] ? sources[item.sourceId].title : '',
        sourceUrl: sources[item.sourceId] ? sources[item.sourceId].url : ''
      });
    });

    return ncpcOk_({
      product: product,
      variants: variants,
      aliases: aliases,
      digitalAssets: assets.filter(function (row) { return !row.variantId; }),
      organizationRelationships: relationships,
      evidence: evidence,
      reviewItems: rows_('ReviewQueue').filter(function (row) { return row.entityId === productId; })
    }, 'Product retrieved');
  } catch (e) {
    return ncpcFail_(e.message, 'PRODUCT_FAILED');
  }
}

function saveNcpcProductBundle(bundle) {
  try {
    initializeNcpcSystem();
    bundle = bundle || {};
    if (!bundle.canonicalName) throw new Error('canonicalName is required');
    if (!bundle.catalogueDomainId) throw new Error('catalogueDomainId is required');
    if (!bundle.categoryId) throw new Error('categoryId is required');

    var product;
    if (bundle.id) {
      product = updateRecord_('Products', bundle.id, {
        catalogueDomainId: bundle.catalogueDomainId,
        categoryId: bundle.categoryId,
        brandId: bundle.brandId || '',
        canonicalName: bundle.canonicalName,
        description: bundle.description || '',
        productType: bundle.productType || 'packaged',
        qualityTier: bundle.qualityTier || 'manually_created',
        verificationStatus: bundle.verificationStatus || 'unverified',
        publicationStatus: bundle.publicationStatus || 'draft',
        status: bundle.status || 'active'
      }, 'UPDATE_PRODUCT');
    } else {
      var duplicate = findStrongProductDuplicate_(bundle);
      if (duplicate) return ncpcFail_('A strong duplicate already exists: ' + duplicate.canonicalName, 'DUPLICATE_PRODUCT');
      product = createRecord_('Products', {
        catalogueDomainId: bundle.catalogueDomainId,
        categoryId: bundle.categoryId,
        brandId: bundle.brandId || '',
        canonicalName: bundle.canonicalName,
        description: bundle.description || '',
        productType: bundle.productType || 'packaged',
        qualityTier: bundle.qualityTier || 'manually_created',
        verificationStatus: bundle.verificationStatus || 'unverified',
        publicationStatus: bundle.publicationStatus || 'draft',
        status: bundle.status || 'active'
      }, 'CREATE_PRODUCT');
    }

    (bundle.variants || []).forEach(function (variant) {
      var savedVariant;
      if (variant.id) {
        savedVariant = updateRecord_('ProductVariants', variant.id, {
          productId: product.id,
          variantName: variant.variantName,
          sizeValue: variant.sizeValue || '',
          sizeUnit: variant.sizeUnit || '',
          salesUnit: variant.salesUnit || '',
          packagingType: variant.packagingType || '',
          inventoryType: variant.inventoryType || 'piece_based',
          verificationStatus: variant.verificationStatus || 'unverified',
          publicationStatus: variant.publicationStatus || 'draft',
          status: variant.status || 'active'
        }, 'UPDATE_PRODUCT_VARIANT');
      } else {
        savedVariant = createRecord_('ProductVariants', {
          productId: product.id,
          variantName: variant.variantName || product.canonicalName,
          sizeValue: variant.sizeValue || '',
          sizeUnit: variant.sizeUnit || '',
          salesUnit: variant.salesUnit || '',
          packagingType: variant.packagingType || '',
          inventoryType: variant.inventoryType || 'piece_based',
          verificationStatus: variant.verificationStatus || product.verificationStatus,
          publicationStatus: variant.publicationStatus || product.publicationStatus,
          status: variant.status || 'active'
        }, 'CREATE_PRODUCT_VARIANT');
      }

      (variant.identifiers || variant.barcodes || []).forEach(function (identifier) {
        var value = identifier.identifierValue || identifier.barcodeValue;
        if (!value) return;
        var existingIdentifier = rows_('Identifiers').filter(function (row) {
          return normalizeText_(row.identifierValue) === normalizeText_(value);
        })[0];
        if (!existingIdentifier) {
          createRecord_('Identifiers', {
            variantId: savedVariant.id,
            identifierType: identifier.identifierType || identifier.barcodeType || 'EAN13',
            identifierValue: value,
            isPrimary: identifier.isPrimary === true || identifier.isPrimary === 'true',
            sourceId: identifier.sourceId || '',
            verificationStatus: identifier.verificationStatus || 'unverified',
            status: identifier.status || 'active'
          }, 'CREATE_IDENTIFIER');
        }
      });
    });

    (bundle.aliases || []).forEach(function (aliasValue) {
      var alias = typeof aliasValue === 'string' ? aliasValue : aliasValue.alias;
      if (!alias) return;
      var exists = rows_('ProductAliases').some(function (row) {
        return row.productId === product.id && normalizeText_(row.alias) === normalizeText_(alias);
      });
      if (!exists) {
        createRecord_('ProductAliases', {
          productId: product.id,
          variantId: '',
          alias: alias,
          languageCode: 'en',
          aliasType: 'alternative_name',
          status: 'active'
        }, 'CREATE_PRODUCT_ALIAS');
      }
    });

    return getNcpcProduct(product.id);
  } catch (e) {
    return ncpcFail_(e.message, 'SAVE_PRODUCT_FAILED');
  }
}

function findStrongProductDuplicate_(bundle) {
  var brandId = bundle.brandId || '';
  var canonical = normalizeText_(bundle.canonicalName);
  return rows_('Products').filter(function (product) {
    return product.brandId === brandId && normalizeText_(product.canonicalName) === canonical && product.status !== 'archived';
  })[0] || null;
}

function publishNcpcProduct(productId, notes) {
  try {
    initializeNcpcSystem();
    var product = getRecord_('Products', productId);
    if (!product) return ncpcFail_('Product not found', 'PRODUCT_NOT_FOUND');
    var variants = rows_('ProductVariants').filter(function (row) { return row.productId === productId && row.status === 'active'; });
    if (!variants.length) return ncpcFail_('A product must have at least one active variant before publication', 'VARIANT_REQUIRED');
    if (product.verificationStatus === 'unverified') return ncpcFail_('Review the product identity before publication', 'REVIEW_REQUIRED');

    updateRecord_('Products', productId, { publicationStatus: 'published', status: 'active' }, 'PUBLISH_PRODUCT');
    variants.forEach(function (variant) {
      updateRecord_('ProductVariants', variant.id, { publicationStatus: 'published' }, 'PUBLISH_PRODUCT_VARIANT');
    });
    closeOpenReviews_('Products', productId, 'published', notes || 'Product published');
    return getNcpcProduct(productId);
  } catch (e) {
    return ncpcFail_(e.message, 'PUBLISH_FAILED');
  }
}

function withdrawNcpcProduct(productId, notes) {
  try {
    updateRecord_('Products', productId, { publicationStatus: 'withdrawn' }, 'WITHDRAW_PRODUCT');
    rows_('ProductVariants').filter(function (row) { return row.productId === productId; }).forEach(function (variant) {
      updateRecord_('ProductVariants', variant.id, { publicationStatus: 'withdrawn' }, 'WITHDRAW_PRODUCT_VARIANT');
    });
    writeAuditEvent_('WITHDRAW_PRODUCT', 'Products', productId, null, null, notes || 'Product withdrawn');
    return getNcpcProduct(productId);
  } catch (e) {
    return ncpcFail_(e.message, 'WITHDRAW_FAILED');
  }
}

/* -------------------------------------------------------------------------- */
/* Organizations, brands, sources and evidence                                */
/* -------------------------------------------------------------------------- */

function saveNcpcOrganization(bundle) {
  try {
    initializeNcpcSystem();
    bundle = bundle || {};
    if (!bundle.legalName) throw new Error('legalName is required');
    var organization = bundle.id
      ? updateRecord_('Organizations', bundle.id, bundle, 'UPDATE_ORGANIZATION')
      : createRecord_('Organizations', {
          legalName: bundle.legalName,
          tradingName: bundle.tradingName || bundle.legalName,
          countryCode: bundle.countryCode || NCPC_APP.defaultMarketCode,
          websiteUrl: bundle.websiteUrl || '',
          description: bundle.description || '',
          verificationStatus: bundle.verificationStatus || 'unverified',
          status: bundle.status || 'active'
        }, 'CREATE_ORGANIZATION');

    (bundle.roles || []).forEach(function (role) {
      if (NCPC_ALLOWED_ORGANIZATION_ROLES.indexOf(role.roleType) < 0) return;
      var existing = rows_('OrganizationRoles').some(function (record) {
        return record.organizationId === organization.id &&
          record.roleType === role.roleType &&
          String(record.territoryCode || '') === String(role.territoryCode || '');
      });
      if (!existing) {
        createRecord_('OrganizationRoles', {
          organizationId: organization.id,
          roleType: role.roleType,
          territoryCode: role.territoryCode || NCPC_APP.defaultMarketCode,
          effectiveFrom: role.effectiveFrom || '',
          effectiveTo: role.effectiveTo || '',
          verificationStatus: role.verificationStatus || organization.verificationStatus,
          status: role.status || 'active'
        }, 'CREATE_ORGANIZATION_ROLE');
      }
    });
    return ncpcOk_(organization, 'Organization saved');
  } catch (e) {
    return ncpcFail_(e.message, 'ORGANIZATION_FAILED');
  }
}

function saveNcpcSource(data) {
  try {
    initializeNcpcSystem();
    if (!data || !data.title) throw new Error('Source title is required');
    var source = data.id
      ? updateRecord_('InformationSources', data.id, data, 'UPDATE_INFORMATION_SOURCE')
      : createRecord_('InformationSources', {
          externalSourceId: data.externalSourceId || '',
          title: data.title,
          url: data.url || '',
          sourceType: data.sourceType || 'other',
          authority: data.authority || 'unverified',
          organizationId: data.organizationId || '',
          documentDate: data.documentDate || '',
          accessedAt: data.accessedAt || nowIso_(),
          notes: data.notes || '',
          status: data.status || 'active'
        }, 'CREATE_INFORMATION_SOURCE');
    return ncpcOk_(source, 'Information source saved');
  } catch (e) {
    return ncpcFail_(e.message, 'SOURCE_FAILED');
  }
}

function addNcpcEvidence(data) {
  try {
    initializeNcpcSystem();
    if (!data.productId) throw new Error('productId is required');
    if (!data.claimType) throw new Error('claimType is required');
    var evidence = createRecord_('CatalogueEvidence', {
      productId: data.productId,
      variantId: data.variantId || '',
      sourceId: data.sourceId || '',
      claimType: data.claimType,
      claimValue: data.claimValue || '',
      evidenceTier: data.evidenceTier || 'manual_review',
      confidence: data.confidence || 'medium',
      verificationStatus: data.verificationStatus || 'unverified',
      reviewNotes: data.reviewNotes || '',
      status: data.status || 'active'
    }, 'CREATE_CATALOGUE_EVIDENCE');
    return ncpcOk_(evidence, 'Evidence added');
  } catch (e) {
    return ncpcFail_(e.message, 'EVIDENCE_FAILED');
  }
}

/* -------------------------------------------------------------------------- */
/* Duplicate detection                                                        */
/* -------------------------------------------------------------------------- */

function findNcpcDuplicates(bundle) {
  try {
    initializeNcpcSystem();
    bundle = bundle || {};
    var identifiers = [];
    (bundle.variants || []).forEach(function (variant) {
      (variant.identifiers || variant.barcodes || []).forEach(function (item) {
        var value = item.identifierValue || item.barcodeValue;
        if (value) identifiers.push(normalizeText_(value));
      });
    });

    var identifierRows = rows_('Identifiers');
    var variants = indexBy_(rows_('ProductVariants'), 'id');
    var products = indexBy_(rows_('Products'), 'id');
    var exactIdentifierMatches = [];
    identifierRows.forEach(function (identifier) {
      if (identifiers.indexOf(normalizeText_(identifier.identifierValue)) >= 0) {
        var variant = variants[identifier.variantId];
        if (variant && products[variant.productId]) exactIdentifierMatches.push(products[variant.productId]);
      }
    });

    var canonical = normalizeText_(bundle.canonicalName || (bundle.product || {}).globalName);
    var brandName = normalizeText_(bundle.brandName || (bundle.brand || {}).name);
    var brands = indexBy_(rows_('Brands'), 'id');
    var strongNameMatches = rows_('Products').filter(function (product) {
      var productBrand = brands[product.brandId] ? normalizeText_(brands[product.brandId].name) : '';
      return canonical && normalizeText_(product.canonicalName) === canonical && (!brandName || productBrand === brandName);
    });

    var possibleMatches = rows_('Products').map(function (product) {
      return {
        product: product,
        score: similarityScore_(canonical, normalizeText_(product.canonicalName))
      };
    }).filter(function (item) {
      return item.score >= 0.62 && strongNameMatches.every(function (match) { return match.id !== item.product.id; });
    }).sort(function (a, b) { return b.score - a.score; }).slice(0, 10);

    return ncpcOk_({
      exactIdentifierMatches: uniqueById_(exactIdentifierMatches),
      strongNameMatches: uniqueById_(strongNameMatches),
      possibleMatches: possibleMatches
    }, 'Duplicate analysis completed');
  } catch (e) {
    return ncpcFail_(e.message, 'DUPLICATE_CHECK_FAILED');
  }
}

function similarityScore_(left, right) {
  if (!left || !right) return 0;
  if (left === right) return 1;
  var leftWords = left.split(' ');
  var rightWords = right.split(' ');
  var intersection = leftWords.filter(function (word) { return rightWords.indexOf(word) >= 0; }).length;
  var union = uniqueValues_(leftWords.concat(rightWords)).length;
  return union ? intersection / union : 0;
}

/* -------------------------------------------------------------------------- */
/* Resumable research manifest imports                                        */
/* -------------------------------------------------------------------------- */

function createNcpcImportJob(manifestInfo, sources) {
  try {
    initializeNcpcSystem();
    manifestInfo = manifestInfo || {};
    if (manifestInfo.schemaVersion !== NCPC_APP.supportedResearchSchema) {
      return ncpcFail_(
        'Unsupported manifest schema. Expected ' + NCPC_APP.supportedResearchSchema,
        'UNSUPPORTED_IMPORT_SCHEMA'
      );
    }

    registerManifestSources_(sources || []);
    var job = createRecord_('ImportJobs', {
      manifestId: manifestInfo.manifestId || '',
      schemaVersion: manifestInfo.schemaVersion,
      fileName: manifestInfo.fileName || 'catalogue-import.json',
      marketCode: manifestInfo.marketCode || manifestInfo.market || NCPC_APP.defaultMarketCode,
      totalItems: Number(manifestInfo.totalItems || 0),
      queuedItems: 0,
      processedItems: 0,
      createdItems: 0,
      mergedItems: 0,
      candidateItems: 0,
      skippedItems: 0,
      failedItems: 0,
      status: 'receiving',
      currentStage: 'receiving_items',
      progressPercent: 0,
      errorSummary: '',
      startedAt: nowIso_(),
      completedAt: ''
    }, 'CREATE_IMPORT_JOB');

    return ncpcOk_(job, 'Import job created');
  } catch (e) {
    return ncpcFail_(e.message, 'IMPORT_JOB_FAILED');
  }
}

function registerManifestSources_(sources) {
  var existingByExternal = {};
  rows_('InformationSources').forEach(function (source) {
    if (source.externalSourceId) existingByExternal[source.externalSourceId] = source;
  });

  sources.forEach(function (source) {
    if (!source || !source.id) return;
    if (existingByExternal[source.id]) return;
    createRecord_('InformationSources', {
      externalSourceId: source.id,
      title: source.title || source.id,
      url: source.url || '',
      sourceType: source.sourceType || 'research_source',
      authority: source.authority || 'unverified',
      organizationId: '',
      documentDate: source.documentDate || '',
      accessedAt: nowIso_(),
      notes: source.notes || '',
      status: 'active'
    }, 'IMPORT_INFORMATION_SOURCE');
  });
}

function appendNcpcImportItems(importJobId, startIndex, bundles) {
  try {
    initializeNcpcSystem();
    var job = getRecord_('ImportJobs', importJobId);
    if (!job) return ncpcFail_('Import job not found', 'IMPORT_JOB_NOT_FOUND');
    if (['completed','cancelled','failed'].indexOf(job.status) >= 0) {
      return ncpcFail_('Import job can no longer receive items', 'IMPORT_JOB_CLOSED');
    }

    bundles = bundles || [];
    var existingItems = rows_('ImportItems').filter(function (item) { return item.importJobId === importJobId; });
    var existingIndexes = {};
    existingItems.forEach(function (item) { existingIndexes[String(item.itemIndex)] = true; });

    var records = [];
    bundles.forEach(function (bundle, offset) {
      var itemIndex = Number(startIndex || 0) + offset;
      if (existingIndexes[String(itemIndex)]) return;
      assertNcpcResearchBundleSafe_(bundle, itemIndex);
      var product = bundle.product || bundle;
      var evidenceTier = getResearchEvidenceTier_(bundle);
      records.push(prepareRecord_('ImportItems', {
        importJobId: importJobId,
        itemIndex: itemIndex,
        externalKey: String(bundle.seedOrder || bundle.expansionOrder || itemIndex),
        rawPayload: JSON.stringify(bundle),
        normalizedName: normalizeText_(product.globalName || product.canonicalName || ''),
        evidenceTier: evidenceTier,
        status: 'queued',
        action: '',
        entityId: '',
        errorMessage: ''
      }, null));
    });

    appendRows_('ImportItems', records);
    var queuedItems = Number(job.queuedItems || 0) + records.length;
    var totalItems = Number(job.totalItems || 0);
    var receivingComplete = totalItems > 0 && queuedItems >= totalItems;
    job = updateRecord_('ImportJobs', importJobId, {
      queuedItems: queuedItems,
      status: receivingComplete ? 'queued' : 'receiving',
      currentStage: receivingComplete ? 'ready_to_process' : 'receiving_items',
      progressPercent: totalItems ? Math.min(10, Math.round((queuedItems / totalItems) * 10)) : 0
    }, 'QUEUE_IMPORT_ITEMS');

    return ncpcOk_({ job: job, appended: records.length }, 'Import items queued');
  } catch (e) {
    return ncpcFail_(e.message, 'IMPORT_ITEMS_FAILED');
  }
}

function doPost(e) {
  try {
    var request = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    var expected = PropertiesService.getScriptProperties().getProperty('NCPC_SUBMISSION_API_TOKEN');
    if (!expected || request.api_token !== expected) throw new Error('Unauthorized');
    if (request.action !== 'submit_candidate') throw new Error('Unsupported action');
    return ncpcJsonOutput_(submitNcpcTradeFlowCandidate(request.data || {}, String(request.business_id || '')));
  } catch (error) { return ncpcJsonOutput_(ncpcFail_(error.message, 'SUBMISSION_FAILED')); }
}

function submitNcpcTradeFlowCandidate(data, businessId) {
  initializeNcpcSystem();
  var safe = { rawName: String(data.rawName || '').trim(), barcode: String(data.barcode || '').trim(), category: String(data.category || '').trim(), referenceUrl: String(data.referenceUrl || '').trim() };
  if (!safe.rawName || safe.rawName.length > 200 || safe.barcode.length > 80 || safe.category.length > 120 || safe.referenceUrl.length > 500) return ncpcFail_('Invalid candidate fields', 'INVALID_CANDIDATE');
  var candidate = createRecord_('ProductCandidates', { originType: 'tradeflow_owner_submission', originReference: businessId, rawName: safe.rawName, rawPayload: JSON.stringify(safe), proposedProductId: '', status: 'pending', reviewNotes: 'Submitted from TradeFlow owner mapping flow; private business fields excluded.', submittedBy: 'tradeflow:' + businessId, submittedAt: nowIso_(), reviewedBy: '', reviewedAt: '' }, 'TRADEFLOW_PRODUCT_CANDIDATE');
  createReviewItem_('product_candidate', 'ProductCandidates', candidate.id, 'normal', 'Review TradeFlow owner product candidate.', 'TRADEFLOW_CANDIDATE_REVIEW');
  return ncpcOk_({ candidateId: candidate.id, status: 'pending' }, 'Candidate submitted for NCPC review');
}

/**
 * Resolves public shared product identity only. It deliberately excludes every
 * TradeFlow-owned price, stock, supplier, cost and financial field.
 */
function findNcpcCandidates(query, options) {
  try {
    initializeNcpcSystem();
    options = options || {};
    var normalizedQuery = normalizeText_(query);
    if (!normalizedQuery) return ncpcCandidateSearchResponse_([], '', 'no_match', [
      'A non-empty product wording, alias, barcode, or size clue is required.'
    ]);
    var queryClues = ncpcQueryClues_(query);
    var requestedLimit = Number(options.limit);
    var limit = !isFinite(requestedLimit) || requestedLimit < 1
      ? 10
      : Math.min(20, Math.floor(requestedLimit));
    var publishedOnly = options.publishedOnly !== false;
    var activeOnly = options.activeOnly !== false;
    var barcodeOnly = options.barcodeOnly === true;
    var products = indexBy_(rows_('Products').filter(function (row) {
      return (!publishedOnly || row.publicationStatus === 'published') && (!activeOnly || row.status === 'active');
    }), 'id');
    var brands = indexBy_(rows_('Brands').filter(function (row) { return !activeOnly || row.status === 'active'; }), 'id');
    var variants = rows_('ProductVariants').filter(function (row) {
      return products[row.productId] && (!publishedOnly || row.publicationStatus === 'published') && (!activeOnly || row.status === 'active');
    });
    var identifiersByVariant = groupBy_(rows_('Identifiers').filter(function (row) { return (!activeOnly || row.status === 'active'); }), 'variantId');
    var aliasesByProduct = groupBy_(rows_('ProductAliases').filter(function (row) { return (!activeOnly || row.status === 'active'); }), 'productId');
    var aliasesByVariant = groupBy_(rows_('ProductAliases').filter(function (row) { return (!activeOnly || row.status === 'active') && row.variantId; }), 'variantId');
    var candidates = variants.map(function (variant) {
      var product = products[variant.productId];
      var identifiers = identifiersByVariant[variant.id] || [];
      var aliases = (aliasesByProduct[product.id] || []).concat(aliasesByVariant[variant.id] || []);
      var exactBarcode = identifiers.some(function (item) { return normalizeText_(item.identifierValue) === normalizedQuery; });
      var exactName = [product.canonicalName, variant.variantName].some(function (item) { return normalizeText_(item) === normalizedQuery; });
      var aliasMatch = aliases.some(function (item) { return normalizeText_(item.alias) === normalizedQuery; });
      var haystack = [product.canonicalName, variant.variantName, brands[product.brandId] ? brands[product.brandId].name : '']
        .concat(aliases.map(function (item) { return item.alias; }))
        .concat(identifiers.map(function (item) { return item.identifierValue; })).join(' ');
      var normalizedHaystack = normalizeText_(haystack);
      var matchedTokens = queryClues.tokens.filter(function(token) { return normalizedHaystack.indexOf(token) >= 0; });
      var allTokensMatch = queryClues.tokens.length && matchedTokens.length === queryClues.tokens.length;
      var fuzzy = ncpcFuzzyTokenMatch_(queryClues.tokens, normalizedHaystack);
      var textMatch = normalizedHaystack.indexOf(normalizedQuery) >= 0;
      if ((barcodeOnly && !exactBarcode) || (!barcodeOnly && !textMatch && !allTokensMatch && !fuzzy)) return null;
      var sizeWarning = '';
      var variantSize = ncpcNormalizedSize_(variant.sizeValue, variant.sizeUnit);
      if (queryClues.size && variantSize && variantSize !== queryClues.size) sizeWarning = 'Requested size does not match this variant.';
      var score = exactBarcode ? 1000 : exactName ? 900 : aliasMatch ? 850 : allTokensMatch ? 700 : fuzzy ? 500 : 300;
      if (sizeWarning) score -= 120;
      var reasons = [];
      if (exactBarcode) reasons.push('identifier_exact'); else if (exactName) reasons.push('canonical_exact'); else if (aliasMatch) reasons.push('alias_exact'); else if (allTokensMatch) reasons.push('all_tokens_match'); else if (fuzzy) reasons.push('fuzzy_spelling_match'); else reasons.push('text_match');
      if (sizeWarning) reasons.push('size_conflict');
      return {
        productId: product.id,
        variantId: variant.id,
        canonicalName: product.canonicalName,
        variantName: variant.variantName,
        brandName: brands[product.brandId] ? brands[product.brandId].name : '',
        sizeValue: variant.sizeValue,
        sizeUnit: variant.sizeUnit,
        salesUnit: variant.salesUnit,
        identifiers: identifiers.map(function (item) { return { type: item.identifierType, value: item.identifierValue, primary: item.isPrimary === 'true' || item.isPrimary === true }; }),
        aliases: aliases.map(function (item) { return item.alias; }),
        matchReason: reasons[0], matchReasons: reasons,
        confidence: score >= 900 ? 'best_match' : score >= 700 ? 'strong_match' : score >= 500 ? 'possible_match' : 'low_confidence',
        warnings: sizeWarning ? [sizeWarning] : [], score: score
      };
    }).filter(function (item) { return item; });
    candidates.sort(function (left, right) { return right.score - left.score || String(left.canonicalName).localeCompare(String(right.canonicalName)); });
    candidates = ncpcDiverseCandidates_(candidates, limit);
    return ncpcCandidateSearchResponse_(candidates, String(query), candidates.length ? 'ok' : 'no_match', candidates.length ? [] : [
      'No published, active catalogue variant matched the supplied clues.'
    ]);
  } catch (e) {
    // Do not expose spreadsheet, authorization, or implementation details to
    // downstream callers. Those details remain available in Apps Script logs.
    Logger.log('Candidate search failed: ' + e.message);
    return ncpcCandidateSearchFailure_('CANDIDATE_SEARCH_FAILED');
  }
}

function ncpcQueryClues_(query) {
  var normalized = normalizeText_(query);
  var sizeMatch = normalized.match(/\b(\d+(?:\.\d+)?)\s*(ml|l|g|kg)\b/);
  return { tokens: normalized.split(' ').filter(function(token) { return token.length > 1 && !/^\d+$/.test(token); }), size: sizeMatch ? ncpcNormalizedSize_(sizeMatch[1], sizeMatch[2]) : '' };
}

function ncpcNormalizedSize_(value, unit) {
  var number = Number(value);
  var normalizedUnit = normalizeText_(unit);
  if (!isFinite(number) || number <= 0 || !normalizedUnit) return '';
  if (normalizedUnit === 'l') return String(number * 1000) + 'ml';
  if (normalizedUnit === 'kg') return String(number * 1000) + 'g';
  return String(number) + normalizedUnit;
}

function ncpcCandidateSearchResponse_(candidates, query, status, warnings) {
  return ncpcOk_({
    contractVersion: NCPC_CANDIDATE_SEARCH_CONTRACT_VERSION,
    status: status,
    query: query,
    candidates: candidates,
    warnings: warnings || [],
    catalogueVersion: getCatalogueVersion_(),
    noneOfTheseSupported: true
  }, status === 'no_match' ? 'No matching published catalogue variant found' : 'Candidate search completed');
}

function ncpcCandidateSearchFailure_(errorCode) {
  return {
    success: false,
    message: 'Candidate search is temporarily unavailable.',
    errorCode: errorCode || 'CANDIDATE_SEARCH_FAILED',
    data: {
      contractVersion: NCPC_CANDIDATE_SEARCH_CONTRACT_VERSION,
      status: 'error',
      candidates: [],
      warnings: []
    },
    catalogueVersion: ncpcSafeCatalogueVersion_(),
    timestamp: nowIso_()
  };
}

function ncpcSafeCatalogueVersion_() {
  try { return getCatalogueVersion_(); } catch (ignore) { return null; }
}

function ncpcFuzzyTokenMatch_(tokens, haystack) {
  var words = haystack.split(' ').filter(Boolean);
  return tokens.length > 0 && tokens.every(function(token) {
    return words.some(function(word) { return token.length >= 4 && ncpcEditDistance_(token, word) <= 1; });
  });
}

function ncpcEditDistance_(left, right) {
  var row = []; for (var i = 0; i <= right.length; i++) row[i] = i;
  for (var a = 1; a <= left.length; a++) { var previous = row[0]; row[0] = a; for (var b = 1; b <= right.length; b++) { var value = Math.min(row[b] + 1, row[b - 1] + 1, previous + (left[a - 1] === right[b - 1] ? 0 : 1)); previous = row[b]; row[b] = value; } }
  return row[right.length];
}

function ncpcDiverseCandidates_(candidates, limit) {
  var familyCounts = {};
  return candidates.filter(function(candidate) { familyCounts[candidate.productId] = (familyCounts[candidate.productId] || 0) + 1; return familyCounts[candidate.productId] <= 2; }).slice(0, limit);
}

function getNcpcPublicProduct_(productId) {
  var product = getRecord_('Products', productId);
  if (!product || product.publicationStatus !== 'published' || product.status !== 'active') return ncpcFail_('Published product not found', 'PUBLIC_PRODUCT_NOT_FOUND');
  var detail = getNcpcProduct(productId);
  if (!detail.success) return detail;
  var data = detail.data;
  data.variants = (data.variants || []).filter(function (variant) { return variant.publicationStatus === 'published' && variant.status === 'active'; });
  delete data.evidence;
  delete data.reviewItems;
  delete data.organizationRelationships;
  return ncpcOk_(data, 'Public product retrieved');
}

/* -------------------------------------------------------------------------- */
/* Read-only downstream catalogue API                                         */
/* -------------------------------------------------------------------------- */

function handleNcpcReadApi_(event, action) {
  try {
    initializeNcpcSystem();
    var params = event && event.parameter ? event.parameter : {};
    var result;
    if (action === 'health') {
      result = ncpcOk_({
        service: 'ncpc-read-api',
        schemaVersion: NCPC_APP.schemaVersion,
        catalogueVersion: getCatalogueVersion_(),
        readOnly: true
      }, 'NCPC read API is healthy');
    } else if (action === 'candidates' || action === 'search') {
      result = findNcpcCandidates(params.q || params.query || '', {
        limit: params.limit,
        publishedOnly: true,
        activeOnly: true
      });
    } else if (action === 'barcode') {
      result = findNcpcCandidates(params.barcode || params.q || '', {
        limit: params.limit || 10,
        publishedOnly: true,
        activeOnly: true,
        barcodeOnly: true
      });
    } else if (action === 'product') {
      result = getNcpcPublicProduct_(params.productId || params.id || '');
    } else {
      result = ncpcFail_('Unsupported read API action', 'API_ACTION_UNSUPPORTED');
    }
    return ncpcJsonOutput_(result);
  } catch (e) {
    if (action === 'candidates' || action === 'search' || action === 'barcode') {
      Logger.log('Public candidate route failed: ' + e.message);
      return ncpcJsonOutput_(ncpcCandidateSearchFailure_('CANDIDATE_SEARCH_FAILED'));
    }
    return ncpcJsonOutput_(ncpcFail_(e.message, 'READ_API_FAILED'));
  }
}

function ncpcJsonOutput_(payload) {
  return ContentService.createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}

function getNcpcIntegrationInfo_() {
  var url = ScriptApp.getService().getUrl() || '';
  return {
    readOnlyCandidateApi: Boolean(url),
    candidateSearchContractVersion: NCPC_CANDIDATE_SEARCH_CONTRACT_VERSION,
    authenticatedSubmissionApi: Boolean(PropertiesService.getScriptProperties().getProperty('NCPC_SUBMISSION_API_TOKEN')),
    writeApiConfigured: false,
    healthUrl: url ? url + '?action=health' : '',
    candidateUrlTemplate: url ? url + '?action=candidates&q={query}' : ''
  };
}

function assertNcpcResearchBundleSafe_(bundle, itemIndex) {
  if (!bundle || typeof bundle !== 'object') throw new Error('Import item ' + itemIndex + ' is empty');
  function scan(value, path) {
    if (!value || typeof value !== 'object') return;
    if (Array.isArray(value)) {
      value.forEach(function (item, index) { scan(item, path + '[' + index + ']'); });
      return;
    }
    Object.keys(value).forEach(function (field) {
      if (NCPC_PROTECTED_TRADEFLOW_FIELDS[ncpcFieldKey_(field)]) {
        throw new Error('Import item ' + itemIndex + ' contains protected TradeFlow field at ' + path + '.' + field);
      }
      scan(value[field], path + '.' + field);
    });
  }
  scan(bundle, 'bundle');
}

function ncpcFieldKey_(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
}

function processNcpcImportBatch(importJobId, requestedBatchSize) {
  try {
    initializeNcpcSystem();
    var job = getRecord_('ImportJobs', importJobId);
    if (!job) return ncpcFail_('Import job not found', 'IMPORT_JOB_NOT_FOUND');
    if (job.status === 'completed') return ncpcOk_({ job: job, processedThisBatch: 0 }, 'Import already completed');
    if (job.status === 'cancelled') return ncpcFail_('Import job was cancelled', 'IMPORT_CANCELLED');

    var batchSize = Math.min(50, Math.max(1, Number(requestedBatchSize || getSettingValue_('defaultImportBatchSize', 25))));
    var queued = rows_('ImportItems').filter(function (item) {
      return item.importJobId === importJobId && item.status === 'queued';
    }).sort(function (a, b) { return Number(a.itemIndex) - Number(b.itemIndex); }).slice(0, batchSize);

    if (!queued.length) {
      var allItems = rows_('ImportItems').filter(function (item) { return item.importJobId === importJobId; });
      var stillWorking = allItems.some(function (item) { return item.status === 'queued' || item.status === 'processing'; });
      if (!stillWorking && Number(job.queuedItems || 0) >= Number(job.totalItems || 0)) {
        job = finalizeImportJob_(job);
        return ncpcOk_({ job: job, processedThisBatch: 0 }, 'Import completed');
      }
      return ncpcOk_({ job: job, processedThisBatch: 0 }, 'No queued items available');
    }

    job = updateRecord_('ImportJobs', importJobId, {
      status: 'processing',
      currentStage: 'normalizing_and_importing'
    }, 'START_IMPORT_BATCH');

    var counters = { created: 0, merged: 0, candidate: 0, skipped: 0, failed: 0 };
    queued.forEach(function (item) {
      try {
        updateRecord_('ImportItems', item.id, { status: 'processing', errorMessage: '' }, 'PROCESS_IMPORT_ITEM');
        var bundle = JSON.parse(item.rawPayload);
        var result = processResearchBundle_(bundle, job);
        counters[result.action] = (counters[result.action] || 0) + 1;
        updateRecord_('ImportItems', item.id, {
          status: 'completed',
          action: result.action,
          entityId: result.entityId || '',
          errorMessage: ''
        }, 'COMPLETE_IMPORT_ITEM');
      } catch (itemError) {
        counters.failed++;
        updateRecord_('ImportItems', item.id, {
          status: 'failed',
          action: 'failed',
          errorMessage: String(itemError.message || itemError).slice(0, 45000)
        }, 'FAIL_IMPORT_ITEM');
      }
    });

    var processedItems = Number(job.processedItems || 0) + queued.length;
    var totalItems = Number(job.totalItems || 0);
    var progress = totalItems ? 10 + Math.round((processedItems / totalItems) * 90) : 0;
    job = updateRecord_('ImportJobs', importJobId, {
      processedItems: processedItems,
      createdItems: Number(job.createdItems || 0) + counters.created,
      mergedItems: Number(job.mergedItems || 0) + counters.merged,
      candidateItems: Number(job.candidateItems || 0) + counters.candidate,
      skippedItems: Number(job.skippedItems || 0) + counters.skipped,
      failedItems: Number(job.failedItems || 0) + counters.failed,
      progressPercent: Math.min(99, progress),
      errorSummary: counters.failed ? counters.failed + ' item(s) failed in the latest batch' : job.errorSummary
    }, 'UPDATE_IMPORT_PROGRESS');

    if (processedItems >= totalItems) job = finalizeImportJob_(job);
    return ncpcOk_({ job: job, processedThisBatch: queued.length, counters: counters }, 'Import batch processed');
  } catch (e) {
    return ncpcFail_(e.message, 'IMPORT_PROCESS_FAILED');
  }
}

function finalizeImportJob_(job) {
  var failed = Number(job.failedItems || 0);
  return updateRecord_('ImportJobs', job.id, {
    status: failed ? 'completed_with_errors' : 'completed',
    currentStage: 'completed',
    progressPercent: 100,
    completedAt: nowIso_()
  }, 'COMPLETE_IMPORT_JOB');
}

function pauseNcpcImportJob(importJobId) {
  try {
    return ncpcOk_(updateRecord_('ImportJobs', importJobId, {
      status: 'paused', currentStage: 'paused_by_user'
    }, 'PAUSE_IMPORT_JOB'), 'Import paused');
  } catch (e) {
    return ncpcFail_(e.message, 'IMPORT_PAUSE_FAILED');
  }
}

function resumeNcpcImportJob(importJobId) {
  try {
    var job = getRecord_('ImportJobs', importJobId);
    if (!job) return ncpcFail_('Import job not found', 'IMPORT_JOB_NOT_FOUND');
    return ncpcOk_(updateRecord_('ImportJobs', importJobId, {
      status: 'queued', currentStage: 'ready_to_process'
    }, 'RESUME_IMPORT_JOB'), 'Import resumed');
  } catch (e) {
    return ncpcFail_(e.message, 'IMPORT_RESUME_FAILED');
  }
}

function cancelNcpcImportJob(importJobId) {
  try {
    return ncpcOk_(updateRecord_('ImportJobs', importJobId, {
      status: 'cancelled', currentStage: 'cancelled_by_user', completedAt: nowIso_()
    }, 'CANCEL_IMPORT_JOB'), 'Import cancelled');
  } catch (e) {
    return ncpcFail_(e.message, 'IMPORT_CANCEL_FAILED');
  }
}

function retryFailedNcpcImportItems(importJobId) {
  try {
    var failedItems = rows_('ImportItems').filter(function (item) {
      return item.importJobId === importJobId && item.status === 'failed';
    });
    failedItems.forEach(function (item) {
      updateRecord_('ImportItems', item.id, {
        status: 'queued', action: '', errorMessage: ''
      }, 'RETRY_IMPORT_ITEM');
    });
    var job = getRecord_('ImportJobs', importJobId);
    if (job) updateRecord_('ImportJobs', importJobId, {
      status: 'queued',
      currentStage: 'retrying_failed_items',
      processedItems: Number(job.processedItems || 0) - failedItems.length,
      failedItems: 0,
      errorSummary: '',
      completedAt: '',
      progressPercent: Math.max(10, Number(job.progressPercent || 0) - 1)
    }, 'RETRY_FAILED_IMPORT_ITEMS');
    return ncpcOk_({ retried: failedItems.length }, 'Failed items re-queued');
  } catch (e) {
    return ncpcFail_(e.message, 'IMPORT_RETRY_FAILED');
  }
}

function processResearchBundle_(bundle, job) {
  bundle = bundle || {};
  assertNcpcResearchBundleSafe_(bundle, '');
  var productData = bundle.product || bundle;
  var evidenceTier = getResearchEvidenceTier_(bundle);
  var canonicalName = String(productData.globalName || productData.canonicalName || '').trim();
  if (!canonicalName) throw new Error('Research bundle has no product name');

  if (evidenceTier === 'market_pack_candidate') {
    var candidate = createRecord_('ProductCandidates', {
      originType: 'research_manifest',
      originReference: job.manifestId || job.id,
      rawName: canonicalName,
      rawPayload: JSON.stringify(bundle),
      proposedProductId: '',
      status: 'pending',
      reviewNotes: 'Market pack-size candidate. Requires physical or authoritative market confirmation.',
      submittedBy: currentUser_(),
      submittedAt: nowIso_(),
      reviewedBy: '',
      reviewedAt: ''
    }, 'IMPORT_PRODUCT_CANDIDATE');
    createReviewItem_('market_confirmation', 'ProductCandidates', candidate.id, 'normal',
      'Confirm that this product variant exists in the target market before promotion.', 'IMPORT_REVIEW_ITEM');
    return { action: 'candidate', entityId: candidate.id };
  }

  var domain = ensureDomainFromResearch_(bundle.businessType || {});
  var category = ensureCategoryFromResearch_(bundle.category || {}, domain.id);
  var organization = ensureOrganizationFromResearch_(bundle.manufacturer || {}, evidenceTier);
  var brand = ensureBrandFromResearch_(bundle.brand || {}, organization, evidenceTier);
  var sourceMap = informationSourceMap_();

  var duplicateBundle = {
    canonicalName: canonicalName,
    brandId: brand ? brand.id : '',
    variants: bundle.variants || []
  };
  var strongDuplicate = findStrongProductDuplicate_(duplicateBundle);
  var possibleDuplicates = strongDuplicate ? [] : findPossibleProductDuplicates_(canonicalName, brand ? brand.id : '');
  var product;
  var action;

  if (strongDuplicate) {
    product = strongDuplicate;
    action = 'merged';
  } else {
    product = createRecord_('Products', {
      catalogueDomainId: domain.id,
      categoryId: category.id,
      brandId: brand ? brand.id : '',
      canonicalName: canonicalName,
      description: productData.description || '',
      productType: productData.productType || 'packaged',
      qualityTier: evidenceTier,
      verificationStatus: evidenceTier === 'official_exact' ? 'reviewed' : 'unverified',
      publicationStatus: 'draft',
      status: 'active'
    }, 'IMPORT_PRODUCT');
    action = 'created';
  }

  if (organization) {
    ensureOrganizationRole_(organization.id, 'manufacturer', job.marketCode || NCPC_APP.defaultMarketCode,
      evidenceTier === 'official_exact' ? 'reviewed' : 'unverified');
    ensureProductOrganizationRelationship_(product.id, '', organization.id, 'manufactured_by', '',
      evidenceTier === 'official_exact' ? 'reviewed' : 'unverified');
    if (brand) ensureBrandOrganizationRelationship_(brand.id, organization.id, 'manufactured_by', '',
      evidenceTier === 'official_exact' ? 'reviewed' : 'unverified');
  }
  importSupplyChainRelationships_(product.id, bundle.research || {}, evidenceTier, job.marketCode || NCPC_APP.defaultMarketCode);
  if (possibleDuplicates.length) {
    createReviewItem_('duplicate_review', 'Products', product.id, 'high',
      'Possible related or duplicate products: ' + possibleDuplicates.map(function (item) {
        return item.product.id + ' (' + item.product.canonicalName + ', score ' + item.score.toFixed(2) + ')';
      }).join('; '), 'IMPORT_REVIEW_ITEM');
  }

  var variants = bundle.variants || [];
  if (!variants.length) variants = [{ variantName: canonicalName }];
  variants.forEach(function (variantData) {
    var existingVariant = findVariantDuplicate_(product.id, variantData);
    var variant = existingVariant || createRecord_('ProductVariants', {
      productId: product.id,
      variantName: variantData.variantName || canonicalName,
      sizeValue: variantData.sizeValue || '',
      sizeUnit: variantData.sizeUnit || '',
      salesUnit: variantData.salesUnit || '',
      packagingType: variantData.packagingType || '',
      inventoryType: variantData.inventoryType || 'piece_based',
      verificationStatus: evidenceTier === 'official_exact' ? 'reviewed' : 'unverified',
      publicationStatus: 'draft',
      status: 'active'
    }, 'IMPORT_PRODUCT_VARIANT');

    (variantData.barcodes || variantData.identifiers || []).forEach(function (identifier) {
      var identifierValue = identifier.barcodeValue || identifier.identifierValue;
      if (!identifierValue) return;
      var sourceId = resolveSourceId_(identifier.sourceId || '', sourceMap);
      var existingIdentifier = rows_('Identifiers').filter(function (row) {
        return normalizeText_(row.identifierValue) === normalizeText_(identifierValue);
      })[0];
      if (!existingIdentifier) {
        createRecord_('Identifiers', {
          variantId: variant.id,
          identifierType: identifier.barcodeType || identifier.identifierType || 'EAN13',
          identifierValue: identifierValue,
          isPrimary: identifier.isPrimary === true || identifier.isPrimary === 'true',
          sourceId: sourceId,
          verificationStatus: identifier.verificationStatus || 'unverified',
          status: 'active'
        }, 'IMPORT_IDENTIFIER');
      }
    });
  });

  (bundle.aliases || []).forEach(function (aliasItem) {
    var alias = typeof aliasItem === 'string' ? aliasItem : aliasItem.alias;
    if (!alias) return;
    var exists = rows_('ProductAliases').some(function (row) {
      return row.productId === product.id && normalizeText_(row.alias) === normalizeText_(alias);
    });
    if (!exists) {
      createRecord_('ProductAliases', {
        productId: product.id,
        variantId: '',
        alias: alias,
        languageCode: 'en',
        aliasType: 'source_alias',
        status: 'active'
      }, 'IMPORT_PRODUCT_ALIAS');
    }
  });

  createResearchEvidence_(product, bundle, evidenceTier, sourceMap);
  createReviewItem_(
    evidenceTier === 'official_exact' ? 'publication_review' : 'identity_review',
    'Products',
    product.id,
    evidenceTier === 'official_exact' ? 'high' : 'normal',
    evidenceTier === 'official_exact'
      ? 'Verify the official product and variant details, then publish when complete.'
      : 'Confirm the product family, variant and market availability before publication.',
    'IMPORT_REVIEW_ITEM'
  );

  return { action: action, entityId: product.id };
}

function getResearchEvidenceTier_(bundle) {
  var research = bundle.research || {};
  if (research.institutionExpansion && research.institutionExpansion.evidenceTier) {
    return research.institutionExpansion.evidenceTier;
  }
  var product = bundle.product || {};
  if (product.verificationStatus === 'reviewed' || product.verificationStatus === 'verified') return 'official_exact';
  return 'institution_linked_family';
}

function ensureDomainFromResearch_(data) {
  var name = data.name || 'Retail & Grocery';
  return findByNormalizedField_('CatalogueDomains', 'name', name) || createRecord_('CatalogueDomains', {
    name: name,
    description: data.description || 'Imported catalogue domain',
    status: data.status || 'active'
  }, 'IMPORT_CATALOGUE_DOMAIN');
}

function ensureCategoryFromResearch_(data, domainId) {
  var name = data.name || 'Uncategorized';
  var existing = rows_('Categories').filter(function (row) {
    return row.catalogueDomainId === domainId && normalizeText_(row.name) === normalizeText_(name);
  })[0];
  if (existing) return existing;
  return createRecord_('Categories', {
    catalogueDomainId: domainId,
    parentCategoryId: '',
    name: name,
    description: data.description || 'Imported controlled category',
    status: data.status || 'active'
  }, 'IMPORT_CATEGORY');
}

function ensureOrganizationFromResearch_(data, evidenceTier) {
  var name = String(data.name || '').trim();
  if (!name) return null;
  var existing = rows_('Organizations').filter(function (row) {
    return normalizeText_(row.legalName) === normalizeText_(name) || normalizeText_(row.tradingName) === normalizeText_(name);
  })[0];
  if (existing) return existing;
  return createRecord_('Organizations', {
    legalName: name,
    tradingName: name,
    countryCode: NCPC_APP.defaultMarketCode,
    websiteUrl: '',
    description: data.description || 'Organization identified during catalogue research',
    verificationStatus: evidenceTier === 'official_exact' ? 'reviewed' : 'unverified',
    status: data.status || 'active'
  }, 'IMPORT_ORGANIZATION');
}

function ensureBrandFromResearch_(data, organization, evidenceTier) {
  var name = String(data.name || '').trim();
  if (!name) return null;
  var brand = findByNormalizedField_('Brands', 'name', name);
  if (!brand) {
    brand = createRecord_('Brands', {
      name: name,
      description: data.description || 'Brand identified during catalogue research',
      verificationStatus: evidenceTier === 'official_exact' ? 'reviewed' : 'unverified',
      status: data.status || 'active'
    }, 'IMPORT_BRAND');
  }
  if (organization) ensureBrandOrganizationRelationship_(brand.id, organization.id, 'manufactured_by', '',
    evidenceTier === 'official_exact' ? 'reviewed' : 'unverified');
  return brand;
}

function ensureOrganizationRole_(organizationId, roleType, territoryCode, verificationStatus) {
  var existing = rows_('OrganizationRoles').filter(function (row) {
    return row.organizationId === organizationId && row.roleType === roleType && row.territoryCode === territoryCode;
  })[0];
  if (existing) return existing;
  return createRecord_('OrganizationRoles', {
    organizationId: organizationId,
    roleType: roleType,
    territoryCode: territoryCode || NCPC_APP.defaultMarketCode,
    effectiveFrom: '',
    effectiveTo: '',
    verificationStatus: verificationStatus || 'unverified',
    status: 'active'
  }, 'IMPORT_ORGANIZATION_ROLE');
}

function ensureBrandOrganizationRelationship_(brandId, organizationId, relationshipType, sourceId, verificationStatus) {
  var existing = rows_('BrandOrganizationRelationships').filter(function (row) {
    return row.brandId === brandId && row.organizationId === organizationId && row.relationshipType === relationshipType;
  })[0];
  if (existing) return existing;
  return createRecord_('BrandOrganizationRelationships', {
    brandId: brandId,
    organizationId: organizationId,
    relationshipType: relationshipType,
    territoryCode: NCPC_APP.defaultMarketCode,
    sourceId: sourceId || '',
    verificationStatus: verificationStatus || 'unverified',
    status: 'active'
  }, 'IMPORT_BRAND_ORGANIZATION_RELATIONSHIP');
}

function ensureProductOrganizationRelationship_(productId, variantId, organizationId, relationshipType, sourceId, verificationStatus) {
  var existing = rows_('ProductOrganizationRelationships').filter(function (row) {
    return row.productId === productId && row.variantId === (variantId || '') &&
      row.organizationId === organizationId && row.relationshipType === relationshipType;
  })[0];
  if (existing) return existing;
  return createRecord_('ProductOrganizationRelationships', {
    productId: productId,
    variantId: variantId || '',
    organizationId: organizationId,
    relationshipType: relationshipType,
    territoryCode: NCPC_APP.defaultMarketCode,
    sourceId: sourceId || '',
    verificationStatus: verificationStatus || 'unverified',
    status: 'active'
  }, 'IMPORT_PRODUCT_ORGANIZATION_RELATIONSHIP');
}

function findPossibleProductDuplicates_(canonicalName, brandId) {
  var normalized = normalizeText_(canonicalName);
  return rows_('Products').map(function (product) {
    var sameBrand = !brandId || !product.brandId || product.brandId === brandId;
    return {
      product: product,
      score: sameBrand ? similarityScore_(normalized, normalizeText_(product.canonicalName)) : 0
    };
  }).filter(function (item) {
    return item.score >= 0.72 && normalizeText_(item.product.canonicalName) !== normalized;
  }).sort(function (left, right) { return right.score - left.score; }).slice(0, 5);
}

function importSupplyChainRelationships_(productId, research, evidenceTier, territoryCode) {
  (research.supplyChain || []).forEach(function (entry) {
    var name = String(entry.name || '').trim();
    if (!name) return;
    var roleType = professionalOrganizationRole_(entry.role || '');
    var relationshipType = professionalProductRelationship_(roleType);
    var organization = ensureOrganizationFromResearch_({
      name: name,
      description: 'Supply-chain organization identified during catalogue research',
      status: 'active'
    }, evidenceTier);
    ensureOrganizationRole_(organization.id, roleType, territoryCode,
      evidenceTier === 'official_exact' ? 'reviewed' : 'unverified');
    ensureProductOrganizationRelationship_(productId, '', organization.id, relationshipType, '',
      evidenceTier === 'official_exact' ? 'reviewed' : 'unverified');
  });
}

function professionalOrganizationRole_(roleText) {
  var normalized = normalizeText_(roleText);
  if (normalized.indexOf('authorized distributor') >= 0) return 'authorized_distributor';
  if (normalized.indexOf('distribut') >= 0 || normalized.indexOf('network') >= 0) return 'distributor';
  if (normalized.indexOf('import') >= 0) return 'importer';
  if (normalized.indexOf('wholesale') >= 0) return 'wholesaler';
  if (normalized.indexOf('supplier') >= 0 || normalized.indexOf('supply') >= 0) return 'supplier';
  if (normalized.indexOf('bottl') >= 0) return 'bottler';
  if (normalized.indexOf('pack') >= 0) return 'packer';
  if (normalized.indexOf('brand owner') >= 0 || normalized.indexOf('owner') >= 0) return 'brand_owner';
  if (normalized.indexOf('manufactur') >= 0) return 'manufacturer';
  return 'data_provider';
}

function professionalProductRelationship_(roleType) {
  var map = {
    authorized_distributor: 'authorized_distributor',
    distributor: 'distributed_by',
    importer: 'imported_by',
    wholesaler: 'supplied_by',
    supplier: 'supplied_by',
    bottler: 'bottled_by',
    packer: 'packed_by',
    brand_owner: 'brand_owned_by',
    manufacturer: 'manufactured_by',
    data_provider: 'data_provided_by'
  };
  return map[roleType] || 'data_provided_by';
}

function findVariantDuplicate_(productId, variantData) {
  var target = [
    normalizeText_(variantData.variantName || ''),
    normalizeText_(variantData.sizeValue || ''),
    normalizeText_(variantData.sizeUnit || ''),
    normalizeText_(variantData.packagingType || '')
  ].join('|');
  return rows_('ProductVariants').filter(function (variant) {
    var key = [
      normalizeText_(variant.variantName || ''),
      normalizeText_(variant.sizeValue || ''),
      normalizeText_(variant.sizeUnit || ''),
      normalizeText_(variant.packagingType || '')
    ].join('|');
    return variant.productId === productId && key === target;
  })[0] || null;
}

function informationSourceMap_() {
  var map = {};
  rows_('InformationSources').forEach(function (source) {
    if (source.externalSourceId) map[source.externalSourceId] = source.id;
    map[source.id] = source.id;
  });
  return map;
}

function resolveSourceId_(externalOrInternalId, sourceMap) {
  return sourceMap[externalOrInternalId] || '';
}

function createResearchEvidence_(product, bundle, evidenceTier, sourceMap) {
  var research = bundle.research || {};
  var sourceIds = research.sourceIds || [];
  if (!sourceIds.length) sourceIds = [''];
  var confidence = research.fieldConfidence || {};
  var claims = [
    { type: 'canonical_name', value: product.canonicalName, confidence: confidence.canonicalName || 'medium' },
    { type: 'brand_identity', value: bundle.brand ? bundle.brand.name : '', confidence: confidence.brand || 'medium' },
    { type: 'manufacturer_identity', value: bundle.manufacturer ? bundle.manufacturer.name : '', confidence: confidence.manufacturer || 'medium' },
    { type: 'variant_identity', value: JSON.stringify(bundle.variants || []), confidence: confidence.variant || 'low' },
    { type: 'barcode_status', value: research.barcodeStatus || 'unknown', confidence: confidence.barcode || 'unknown' },
    { type: 'publication_gate', value: research.publicationGate || 'manual_review_required', confidence: 'high' }
  ];

  claims.forEach(function (claim) {
    if (!claim.value) return;
    sourceIds.forEach(function (sourceExternalId) {
      var sourceId = resolveSourceId_(sourceExternalId, sourceMap);
      var duplicate = rows_('CatalogueEvidence').some(function (row) {
        return row.productId === product.id && row.sourceId === sourceId &&
          row.claimType === claim.type && String(row.claimValue) === String(claim.value);
      });
      if (!duplicate) {
        createRecord_('CatalogueEvidence', {
          productId: product.id,
          variantId: '',
          sourceId: sourceId,
          claimType: claim.type,
          claimValue: String(claim.value).slice(0, 45000),
          evidenceTier: evidenceTier,
          confidence: claim.confidence,
          verificationStatus: evidenceTier === 'official_exact' ? 'reviewed' : 'unverified',
          reviewNotes: (research.reviewNotes || []).join('; '),
          status: 'active'
        }, 'IMPORT_CATALOGUE_EVIDENCE');
      }
    });
  });
}

/* -------------------------------------------------------------------------- */
/* Review workflow                                                            */
/* -------------------------------------------------------------------------- */

function createReviewItem_(queueType, entityType, entityId, priority, reason, auditAction) {
  var existing = rows_('ReviewQueue').filter(function (row) {
    return row.queueType === queueType && row.entityType === entityType && row.entityId === entityId &&
      (row.status === 'pending' || row.status === 'in_progress');
  })[0];
  if (existing) return existing;
  return createRecord_('ReviewQueue', {
    queueType: queueType,
    entityType: entityType,
    entityId: entityId,
    priority: priority || 'normal',
    reason: reason || '',
    status: 'pending',
    assignedTo: '',
    dueAt: '',
    resolution: '',
    resolutionNotes: ''
  }, auditAction || 'CREATE_REVIEW_ITEM');
}

function getNcpcReviewQueue(filters) {
  try {
    initializeNcpcSystem();
    filters = filters || {};
    var records = rows_('ReviewQueue');
    Object.keys(filters).forEach(function (key) {
      if (!filters[key]) return;
      records = records.filter(function (row) { return String(row[key]) === String(filters[key]); });
    });
    records.sort(function (a, b) {
      var priorityOrder = { critical: 4, high: 3, normal: 2, low: 1 };
      return (priorityOrder[b.priority] || 0) - (priorityOrder[a.priority] || 0) ||
        String(a.createdAt).localeCompare(String(b.createdAt));
    });
    return ncpcOk_(records, 'Review queue retrieved');
  } catch (e) {
    return ncpcFail_(e.message, 'REVIEW_QUEUE_FAILED');
  }
}

function getNcpcReviewContext(reviewId) {
  try {
    initializeNcpcSystem();
    var review = getRecord_('ReviewQueue', reviewId);
    if (!review) return ncpcFail_('Review item not found', 'REVIEW_NOT_FOUND');
    var entity = null;
    if (NCPC_TABLES[review.entityType]) entity = getRecord_(review.entityType, review.entityId);
    var productContext = null;
    if (review.entityType === 'Products') productContext = getNcpcProduct(review.entityId).data;
    if (review.entityType === 'ProductCandidates' && entity) {
      try { entity.parsedPayload = JSON.parse(entity.rawPayload); } catch (ignore) {}
    }
    return ncpcOk_({ review: review, entity: entity, productContext: productContext }, 'Review context retrieved');
  } catch (e) {
    return ncpcFail_(e.message, 'REVIEW_CONTEXT_FAILED');
  }
}

function resolveNcpcReview(reviewId, resolution, notes) {
  try {
    initializeNcpcSystem();
    var review = getRecord_('ReviewQueue', reviewId);
    if (!review) return ncpcFail_('Review item not found', 'REVIEW_NOT_FOUND');
    var result = null;

    if (review.entityType === 'Products') {
      if (resolution === 'approve_identity') {
        result = updateRecord_('Products', review.entityId, {
          verificationStatus: 'reviewed', publicationStatus: 'in_review'
        }, 'APPROVE_PRODUCT_IDENTITY');
      } else if (resolution === 'publish') {
        var publishResult = publishNcpcProduct(review.entityId, notes);
        if (!publishResult.success) return publishResult;
        result = publishResult.data.product;
      } else if (resolution === 'reject') {
        result = updateRecord_('Products', review.entityId, {
          publicationStatus: 'rejected', status: 'inactive'
        }, 'REJECT_PRODUCT');
      } else if (resolution === 'request_information') {
        result = updateRecord_('Products', review.entityId, {
          publicationStatus: 'in_review'
        }, 'REQUEST_PRODUCT_INFORMATION');
      }
    } else if (review.entityType === 'ProductCandidates') {
      if (resolution === 'promote_candidate') {
        var promoteResult = promoteNcpcCandidate(review.entityId);
        if (!promoteResult.success) return promoteResult;
        result = promoteResult.data;
      } else if (resolution === 'reject') {
        result = updateRecord_('ProductCandidates', review.entityId, {
          status: 'rejected', reviewNotes: notes || 'Candidate rejected',
          reviewedBy: currentUser_(), reviewedAt: nowIso_()
        }, 'REJECT_PRODUCT_CANDIDATE');
      } else if (resolution === 'request_information') {
        result = updateRecord_('ProductCandidates', review.entityId, {
          status: 'more_information_required', reviewNotes: notes || ''
        }, 'REQUEST_CANDIDATE_INFORMATION');
      }
    }

    var finalStatus = resolution === 'request_information' ? 'waiting_for_information' : 'resolved';
    updateRecord_('ReviewQueue', reviewId, {
      status: finalStatus,
      resolution: resolution,
      resolutionNotes: notes || '',
      assignedTo: currentUser_()
    }, 'RESOLVE_REVIEW_ITEM');

    return ncpcOk_({ reviewId: reviewId, resolution: resolution, result: result }, 'Review resolved');
  } catch (e) {
    return ncpcFail_(e.message, 'REVIEW_RESOLUTION_FAILED');
  }
}

function closeOpenReviews_(entityType, entityId, resolution, notes) {
  rows_('ReviewQueue').filter(function (row) {
    return row.entityType === entityType && row.entityId === entityId &&
      (row.status === 'pending' || row.status === 'in_progress');
  }).forEach(function (review) {
    updateRecord_('ReviewQueue', review.id, {
      status: 'resolved',
      resolution: resolution,
      resolutionNotes: notes || '',
      assignedTo: currentUser_()
    }, 'AUTO_CLOSE_REVIEW');
  });
}

function promoteNcpcCandidate(candidateId) {
  try {
    initializeNcpcSystem();
    var candidate = getRecord_('ProductCandidates', candidateId);
    if (!candidate) return ncpcFail_('Candidate not found', 'CANDIDATE_NOT_FOUND');
    var bundle = JSON.parse(candidate.rawPayload);
    var originalResearch = bundle.research || {};
    if (originalResearch.institutionExpansion) {
      originalResearch.institutionExpansion.evidenceTier = 'institution_linked_family';
      originalResearch.institutionExpansion.candidateType = 'human_promoted_market_candidate';
    }
    bundle.research = originalResearch;
    var pseudoJob = { id: 'MANUAL', manifestId: candidate.originReference, marketCode: NCPC_APP.defaultMarketCode };
    var result = processResearchBundle_(bundle, pseudoJob);
    updateRecord_('ProductCandidates', candidateId, {
      proposedProductId: result.entityId,
      status: 'promoted',
      reviewNotes: 'Promoted to draft product after human review',
      reviewedBy: currentUser_(),
      reviewedAt: nowIso_()
    }, 'PROMOTE_PRODUCT_CANDIDATE');
    return ncpcOk_({ candidateId: candidateId, productId: result.entityId }, 'Candidate promoted to draft product');
  } catch (e) {
    return ncpcFail_(e.message, 'CANDIDATE_PROMOTION_FAILED');
  }
}

/* -------------------------------------------------------------------------- */
/* Barcode verification                                                       */
/* -------------------------------------------------------------------------- */

function submitBarcodeForVerification(data) {
  try {
    initializeNcpcSystem();
    data = data || {};
    if (!data.variantId) throw new Error('variantId is required');
    if (!data.identifierValue) throw new Error('identifierValue is required');

    var existingIdentifier = rows_('Identifiers').filter(function (row) {
      return normalizeText_(row.identifierValue) === normalizeText_(data.identifierValue);
    })[0];
    if (existingIdentifier) return ncpcFail_('Identifier already exists on variant ' + existingIdentifier.variantId, 'IDENTIFIER_EXISTS');

    var existingQueue = rows_('BarcodeVerificationQueue').filter(function (row) {
      return normalizeText_(row.identifierValue) === normalizeText_(data.identifierValue) && row.status === 'pending';
    })[0];
    if (existingQueue) return ncpcFail_('This identifier is already awaiting verification', 'VERIFICATION_PENDING');

    var queueItem = createRecord_('BarcodeVerificationQueue', {
      variantId: data.variantId,
      identifierValue: data.identifierValue,
      identifierType: data.identifierType || 'EAN13',
      submittedBy: data.submittedBy || currentUser_(),
      submissionSource: data.submissionSource || 'manual_entry',
      photoUrl: data.photoUrl || '',
      sourceId: data.sourceId || '',
      status: 'pending',
      verificationNotes: '',
      verifiedBy: '',
      verifiedAt: ''
    }, 'SUBMIT_BARCODE_VERIFICATION');

    createReviewItem_('barcode_verification', 'BarcodeVerificationQueue', queueItem.id, 'high',
      'Confirm the barcode against the physical product or an authoritative source.');
    return ncpcOk_(queueItem, 'Barcode submitted for verification');
  } catch (e) {
    return ncpcFail_(e.message, 'BARCODE_SUBMISSION_FAILED');
  }
}

function resolveBarcodeVerification(queueId, decision, notes) {
  try {
    initializeNcpcSystem();
    var queueItem = getRecord_('BarcodeVerificationQueue', queueId);
    if (!queueItem) return ncpcFail_('Barcode verification item not found', 'BARCODE_QUEUE_NOT_FOUND');
    if (queueItem.status !== 'pending') return ncpcFail_('Barcode verification has already been resolved', 'BARCODE_ALREADY_RESOLVED');

    var identifier = null;
    if (decision === 'verify') {
      var duplicate = rows_('Identifiers').filter(function (row) {
        return normalizeText_(row.identifierValue) === normalizeText_(queueItem.identifierValue);
      })[0];
      if (duplicate) return ncpcFail_('Identifier already belongs to variant ' + duplicate.variantId, 'IDENTIFIER_EXISTS');
      identifier = createRecord_('Identifiers', {
        variantId: queueItem.variantId,
        identifierType: queueItem.identifierType || 'EAN13',
        identifierValue: queueItem.identifierValue,
        isPrimary: false,
        sourceId: queueItem.sourceId || '',
        verificationStatus: 'verified',
        status: 'active'
      }, 'VERIFY_BARCODE');
    }

    updateRecord_('BarcodeVerificationQueue', queueId, {
      status: decision === 'verify' ? 'verified' : 'rejected',
      verificationNotes: notes || '',
      verifiedBy: currentUser_(),
      verifiedAt: nowIso_()
    }, decision === 'verify' ? 'APPROVE_BARCODE_VERIFICATION' : 'REJECT_BARCODE_VERIFICATION');

    closeOpenReviews_('BarcodeVerificationQueue', queueId, decision, notes || 'Barcode verification resolved');
    return ncpcOk_({ queueId: queueId, identifier: identifier, decision: decision }, 'Barcode verification resolved');
  } catch (e) {
    return ncpcFail_(e.message, 'BARCODE_VERIFICATION_FAILED');
  }
}

/* -------------------------------------------------------------------------- */
/* Releases and exports                                                       */
/* -------------------------------------------------------------------------- */

function createNcpcRelease(releaseName, description) {
  try {
    initializeNcpcSystem();
    var products = rows_('Products').filter(function (row) {
      return row.publicationStatus === 'published' && row.status === 'active';
    });
    var productIds = products.map(function (row) { return row.id; });
    var variants = rows_('ProductVariants').filter(function (row) {
      return productIds.indexOf(row.productId) >= 0 && row.publicationStatus === 'published' && row.status === 'active';
    });
    var releaseVersion = 'NCPC-' + Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyyMMdd-HHmmss');
    var release = createRecord_('CatalogueReleases', {
      releaseName: releaseName || releaseVersion,
      releaseVersion: releaseVersion,
      description: description || '',
      status: 'published',
      productCount: products.length,
      variantCount: variants.length,
      publishedAt: nowIso_(),
      publishedBy: currentUser_()
    }, 'CREATE_CATALOGUE_RELEASE');

    var releaseItems = [];
    products.forEach(function (product) {
      releaseItems.push({
        id: nextId_('ReleaseItems'),
        releaseId: release.id,
        entityType: 'Products',
        entityId: product.id,
        entityVersion: product.version,
        createdAt: nowIso_(),
        createdBy: currentUser_()
      });
    });
    variants.forEach(function (variant) {
      releaseItems.push({
        id: nextId_('ReleaseItems'),
        releaseId: release.id,
        entityType: 'ProductVariants',
        entityId: variant.id,
        entityVersion: variant.version,
        createdAt: nowIso_(),
        createdBy: currentUser_()
      });
    });
    appendRows_('ReleaseItems', releaseItems);
    writeAuditEvent_('CREATE_RELEASE_ITEMS', 'CatalogueReleases', release.id, null,
      { itemCount: releaseItems.length }, 'Published catalogue release snapshot');
    return ncpcOk_(release, 'Catalogue release created');
  } catch (e) {
    return ncpcFail_(e.message, 'RELEASE_FAILED');
  }
}

function exportNcpcCatalogue(options) {
  try {
    initializeNcpcSystem();
    options = options || {};
    var publishedOnly = options.publishedOnly !== false;
    var products = rows_('Products').filter(function (row) {
      return !publishedOnly || (row.publicationStatus === 'published' && row.status === 'active');
    });
    var productIds = products.map(function (row) { return row.id; });
    var variants = rows_('ProductVariants').filter(function (row) {
      return productIds.indexOf(row.productId) >= 0 && (!publishedOnly || (row.publicationStatus === 'published' && row.status === 'active'));
    });
    var variantIds = variants.map(function (row) { return row.id; });

    var exportData = {
      schemaVersion: NCPC_APP.schemaVersion,
      catalogueId: 'NCPC-ZM',
      catalogueVersion: getCatalogueVersion_(),
      exportedAt: nowIso_(),
      publishedOnly: publishedOnly,
      catalogueDomains: rows_('CatalogueDomains'),
      categories: rows_('Categories'),
      organizations: rows_('Organizations'),
      organizationRoles: rows_('OrganizationRoles'),
      brands: rows_('Brands'),
      brandOrganizationRelationships: rows_('BrandOrganizationRelationships'),
      products: products,
      productVariants: variants,
      identifiers: rows_('Identifiers').filter(function (row) { return variantIds.indexOf(row.variantId) >= 0; }),
      productAliases: rows_('ProductAliases').filter(function (row) { return productIds.indexOf(row.productId) >= 0; }),
      digitalAssets: rows_('DigitalAssets').filter(function (row) { return productIds.indexOf(row.productId) >= 0; }),
      productOrganizationRelationships: rows_('ProductOrganizationRelationships').filter(function (row) { return productIds.indexOf(row.productId) >= 0; }),
      informationSources: rows_('InformationSources'),
      catalogueEvidence: rows_('CatalogueEvidence').filter(function (row) { return productIds.indexOf(row.productId) >= 0; }),
      releases: rows_('CatalogueReleases')
    };
    writeAuditEvent_('EXPORT_CATALOGUE', 'Catalogue', 'NCPC-ZM', null,
      { publishedOnly: publishedOnly, productCount: products.length }, 'Catalogue exported');
    return ncpcOk_(exportData, 'Catalogue export prepared');
  } catch (e) {
    return ncpcFail_(e.message, 'EXPORT_FAILED');
  }
}

function createReleaseFromMenu_() {
  var ui = SpreadsheetApp.getUi();
  var nameResult = ui.prompt('Create NCPC Release', 'Release name:', ui.ButtonSet.OK_CANCEL);
  if (nameResult.getSelectedButton() !== ui.Button.OK) return;
  var result = createNcpcRelease(nameResult.getResponseText(), 'Created from spreadsheet menu');
  ui.alert(result.success ? 'Release created: ' + result.data.releaseVersion : result.message);
}

function exportPublishedCatalogueFromMenu_() {
  var result = exportNcpcCatalogue({ publishedOnly: true });
  SpreadsheetApp.getUi().alert(result.success
    ? 'Published catalogue prepared. Use the web app Export screen to download the JSON file.'
    : result.message);
}

/* -------------------------------------------------------------------------- */
/* Audit and utilities                                                        */
/* -------------------------------------------------------------------------- */

function writeAuditEvent_(action, entityType, entityId, oldValue, newValue, notes) {
  try {
    var record = {
      id: nextId_('AuditEvents'),
      timestamp: nowIso_(),
      userEmail: currentUser_(),
      action: action,
      entityType: entityType || '',
      entityId: entityId || '',
      oldValue: oldValue ? JSON.stringify(oldValue).slice(0, 45000) : '',
      newValue: newValue ? JSON.stringify(newValue).slice(0, 45000) : '',
      notes: notes || ''
    };
    appendRows_('AuditEvents', [record]);
  } catch (e) {
    Logger.log('Audit event failed: ' + e.message);
  }
}

function indexBy_(records, field) {
  var index = {};
  records.forEach(function (record) { index[record[field]] = record; });
  return index;
}

function groupBy_(records, field) {
  var groups = {};
  records.forEach(function (record) {
    var key = record[field] || '';
    if (!groups[key]) groups[key] = [];
    groups[key].push(record);
  });
  return groups;
}

function uniqueValues_(values) {
  var seen = {};
  return values.filter(function (value) {
    if (seen[value]) return false;
    seen[value] = true;
    return true;
  });
}

function uniqueById_(records) {
  var seen = {};
  return records.filter(function (record) {
    if (!record || seen[record.id]) return false;
    seen[record.id] = true;
    return true;
  });
}

function ncpcOk_(data, message) {
  return {
    success: true,
    message: message || 'Request completed',
    data: data,
    catalogueVersion: getCatalogueVersion_(),
    timestamp: nowIso_()
  };
}

function ncpcFail_(message, errorCode) {
  var version = 1;
  try { version = getCatalogueVersion_(); } catch (ignore) {}
  return {
    success: false,
    message: String(message || 'Unknown error'),
    errorCode: errorCode || 'NCPC_ERROR',
    data: null,
    catalogueVersion: version,
    timestamp: nowIso_()
  };
}

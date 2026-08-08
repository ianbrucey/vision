app.openflis.com
OpenFLIS
8–10 minutes

Core Concepts

Understand the foundational concepts behind the OpenFLIS API: how requests are structured, how data is organized, and how to work with responses.

Lookup Keys

Every API request starts with a lookup key. The key determines which set of data tables you can query.
Key	Format	Description	Example
NIIN	9-digit string	National Item Identification Number. The most common key and the one that unlocks the widest range of item-level data.	012345678
FSC	4-digit string	Federal Supply Classification. Groups items by physical or performance characteristics.	5961
CAGE_CODE	5-char string	Commercial and Government Entity Code. Identifies manufacturers and suppliers.	1ABC2
INC	5-digit string	Item Name Code. Standardized classification for item naming.	07283
DODIC	4-char string	Department of Defense Identification Code. Ammunition-specific identifier.	A059
CODE	Up to 5 chars	General code lookups for definitions and contextual help.	AAC

Tables & Data Structure

Data in the OpenFLIS API is organized into tables. Each table belongs to a lookup key and contains a specific set of fields.
Key -> Table relationship

NIIN -> NSN, IDENTIFICATION, MANAGEMENT, PART, ...
FSC  -> H2_PICK, H2_FSG, H2_FSC
CAGE -> CAGE, CAGE_ADDRESS, H5_CORPORATE, H5_DOMESTIC, H5_FOREIGN, ...
INC  -> H6_PICK, H6_NAME_INC, H6_RELATED, COLLOQUIAL_NAME, ...
DODIC -> H3_AMMUNITION
CODE -> HELP

Table types

    Picklist tables return a summary row for quick lookups, such as NSN, H2_PICK, and H5_PICK.
    Detail tables return in-depth data for a single record, such as IDENTIFICATION, CHARACTERISTICS, and CAGE_ADDRESS.
    History tables return historical records that show how data has changed over time, such as HISTORY_PICK and MANAGEMENT_HISTORY.

Fields

Each table has a defined set of fields. Field definitions returned by the schema endpoint include:
Attribute	Description
name	The field identifier used in API responses, such as ITEM_NAME or CAGE_CODE.
displayName	Human-readable label for the field.
type	Logical field type exposed by the schema, such as string, number, date, boolean, or price.
isKey	Whether this field is the primary key for the table.
isUnique	Whether this field is part of the unique identity for the record.
foreignKey	If present, this field references another lookup key, such as a CAGE_CODE field linking a NIIN record to CAGE data.

Endpoints

The API provides four core GET endpoints.
Data query endpoint - /v1/query

Look up records by key and table using query parameters:

GET https://app.openflis.com/api/v1/query?table=[TABLE_NAME]&key=[VALUE]&apiKey=[YOUR_API_KEY]

Or pass the API key as a header instead of a query parameter:

curl "https://app.openflis.com/api/v1/query?table=NSN&key=012345678" 
  -H "API-KEY: $OPENFLIS_API_KEY"

Parameter	Required	Description
table	Yes	The data table to query, such as NSN, MANAGEMENT, or CAGE. See the Data Tables Reference for the full list.
key	Yes	The lookup value for the table's key category, such as a 9-digit NIIN or 5-character CAGE code.
apiKey	Yes, or use the API-KEY header	Your active OpenFLIS API key.
NIIN lookup by part endpoint - /v1/query/parts

Look up candidate NIINs from an exact manufacturer part number and CAGE code:

GET https://app.openflis.com/api/v1/query/parts?partNumber=[PART_NUMBER]&cageCode=[CAGE_CODE]&apiKey=[YOUR_API_KEY]

Or pass the API key as a header:

curl "https://app.openflis.com/api/v1/query/parts?partNumber=ABC123&cageCode=1ABC2" 
  -H "API-KEY: $OPENFLIS_API_KEY"

Part numbers are not globally unique, so this endpoint requires both partNumber and cageCode. The response uses the same query response shape as other data calls and can return zero, one, or multiple matching PART records.
Parameter	Required	Description
partNumber	Yes	The exact manufacturer or reference part number to look up.
cageCode	Yes	The 5-character CAGE code that identifies the manufacturer or design-control entity.
apiKey	Yes, or use the API-KEY header	Your active OpenFLIS API key.
Parts by CAGE endpoint - /v1/query/parts/by-cage

List part reference records for a CAGE code in fixed 100-row pages:

curl "https://app.openflis.com/api/v1/query/parts/by-cage?cageCode=1ABC2" 
  -H "API-KEY: $OPENFLIS_API_KEY"

Omit start for the first 100 rows. Use the response's nextStart value to request the next page.
Schema endpoint - /v1/product

Retrieve the complete product schema with all available keys, tables, and fields:

GET https://app.openflis.com/api/v1/product?apiKey=[YOUR_API_KEY]

This response describes the full data model and is useful for programmatically discovering available keys, tables, and fields.

Response Format

Query and schema responses are intentionally simple and predictable.
Query response

Data query responses follow this structure:

{
  "name": "NSN",
  "value": "012345678",
  "records": [
    {
      "FSC": "5961",
      "INC": "07283",
      "ITEM_NAME": "SEMICONDUCTOR DEVICE, DIODE",
      "SOS": "DEFENSE LOGISTICS AGENCY",
      "END_ITEM_NAME": "",
      "CANCELLED_NIIN": ""
    }
  ]
}

Field	Type	Description
name	string	The table that was queried.
value	string	The lookup value that was searched.
records	array	An array of result objects. Each record contains the table's non-key fields.
Schema response

The /v1/product endpoint returns the full data model:

{
  "name": "PUBLOG",
  "data": {
    "schemaDate": "2023-01-01T00:00:00",
    "keys": [
      {
        "name": "NIIN",
        "tables": [
          {
            "name": "NSN",
            "displayName": "FLIS NSN",
            "description": "...",
            "isNormalized": true,
            "isPicklist": false,
            "fields": [ ... ]
          }
        ]
      }
    ]
  }
}

Conventions

    All query result values are returned as strings, regardless of their logical type.
    Empty fields return "".
    Price fields, such as UNIT_PRICE, are returned as string-encoded numbers.
    The lookup key value is returned once as the top-level value and omitted from individual records.
    Tables where isNormalized is false, such as CHARACTERISTICS and REFERENCE_NUMBER_HISTORY, may require combining unique fields to identify a single record.

Rate Limits

The API enforces plan-based usage limits per API key to ensure consistent performance.
Limit	Value	Notes
Monthly credit cap	100 Free, 2,000 Starter, 10,000 Pro, 25,000+ Enterprise	Check your dashboard for your current shared web app and API balance.
Over-limit response	429	Returned when the account exceeds its shared monthly credit cap.

Usage is enforced at the API key level. The current API does not expose dedicated X-RateLimit-* response headers, so monitor usage in the dashboard and handle 429 responses gracefully.

Bulk & Batch Queries

The API does not have a dedicated bulk endpoint. Each request queries one table and one key value combination.
Recommended approach

    Parallelize within your plan limits. Use a small pool of concurrent HTTP clients instead of sending requests strictly one at a time.
    Prioritize picklist tables. Start with tables like NSN or H5_PICK to validate identifiers before requesting detail tables.
    Cache aggressively. Reference data such as HELP, H2_FSC, and many CAGE records changes only with monthly releases.
    Monitor usage and back off on 429 responses instead of retrying immediately.

Example: Batch NIIN validation (Python)

import os
import requests
from concurrent.futures import ThreadPoolExecutor

api_key = os.environ["OPENFLIS_API_KEY"]
headers = {"API-KEY": api_key}

def validate_niin(niin):
    response = requests.get(
        "https://app.openflis.com/api/v1/query",
        params={"table": "NSN", "key": niin},
        headers=headers,
    )
    return {
        "niin": niin,
        "status": response.status_code,
        "data": response.json(),
    }

niins = ["012345678", "987654321", "555555555"]

# Process a small number concurrently and back off on 429s if needed.

with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(validate_niin, niins))

for result in results:
    print(result["niin"], result["status"])

class AccountModel {
  final String id;
  final String code;
  final String name;
  final String type;
  final String normalBalance;

  AccountModel({
    required this.id,
    required this.code,
    required this.name,
    required this.type,
    required this.normalBalance,
  });

  factory AccountModel.fromJson(Map<String, dynamic> json) {
    return AccountModel(
      id: json['id'] as String,
      code: json['code'] as String,
      name: json['name'] as String,
      type: json['type'] as String,
      normalBalance: json['normalBalance'] as String,
    );
  }
}

class JournalEntryModel {
  final String id;
  final String journalTransactionId;
  final String accountId;
  final String accountCode;
  final String accountName;
  final String debit;
  final String credit;

  JournalEntryModel({
    required this.id,
    required this.journalTransactionId,
    required this.accountId,
    required this.accountCode,
    required this.accountName,
    required this.debit,
    required this.credit,
  });

  factory JournalEntryModel.fromJson(Map<String, dynamic> json) {
    return JournalEntryModel(
      id: json['id'] as String,
      journalTransactionId: json['journalTransactionId'] as String,
      accountId: json['accountId'] as String,
      accountCode: json['accountCode'] as String,
      accountName: json['accountName'] as String,
      debit: json['debit'].toString(),
      credit: json['credit'].toString(),
    );
  }
}

class JournalTransactionModel {
  final String id;
  final String eventType;
  final String? sourceId;
  final String description;
  final String effectiveDate;
  final String postedAt;
  final String? reversalOfId;
  final String totalDebit;
  final String totalCredit;
  final bool isBalanced;
  final List<JournalEntryModel> entries;

  JournalTransactionModel({
    required this.id,
    required this.eventType,
    this.sourceId,
    required this.description,
    required this.effectiveDate,
    required this.postedAt,
    this.reversalOfId,
    required this.totalDebit,
    required this.totalCredit,
    required this.isBalanced,
    required this.entries,
  });

  factory JournalTransactionModel.fromJson(Map<String, dynamic> json) {
    final entriesRaw = json['entries'] as List<dynamic>? ?? [];
    return JournalTransactionModel(
      id: json['id'] as String,
      eventType: json['eventType'] as String,
      sourceId: json['sourceId'] as String?,
      description: json['description'] as String,
      effectiveDate: json['effectiveDate'] as String,
      postedAt: json['postedAt'] as String,
      reversalOfId: json['reversalOfId'] as String?,
      totalDebit: json['totalDebit'].toString(),
      totalCredit: json['totalCredit'].toString(),
      isBalanced: json['isBalanced'] as bool? ?? true,
      entries: entriesRaw
          .map((e) => JournalEntryModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

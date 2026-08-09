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
      type: json['account_type'] as String,
      normalBalance: json['normal_balance'] as String,
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
      journalTransactionId: json['journal_transaction_id'] as String,
      accountId: json['account_id'] as String,
      accountCode: json['account_code'] as String,
      accountName: json['account_name'] as String,
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
      eventType: json['event_type'] as String,
      sourceId: json['source_id'] as String?,
      description: json['description'] as String,
      effectiveDate: json['effective_date'] as String,
      postedAt: json['posted_at'] as String,
      reversalOfId: json['reversal_of_id'] as String?,
      totalDebit: json['total_debit'].toString(),
      totalCredit: json['total_credit'].toString(),
      isBalanced: json['is_balanced'] as bool? ?? true,
      entries: entriesRaw
          .map((e) => JournalEntryModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

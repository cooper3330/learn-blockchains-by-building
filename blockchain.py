import hashlib
import json
from time import time
from textwrap import dedent
from uuid import uuid4
from flask import Flask, jsonify, request

class Blockchain(object):

    def __init__(self):
        self.chain = []
        self.current_transactions = []

        # Create Genesis Block
        self.new_block(proof=100, previous_hash=1))

    def new_block(self, proof, previous_hash=None):
	"""
	Create a new Block in the Blockchain
    :param proof: <int> The proof given by the Proof of Work algorithm
    :param previous_hash: (Optional) <str> Hash of previous Block
    :return: <dict> New Block
    """

	block = {
        'index' : len(self.chain) + 1,
        'transations' : self.current_transactions,
        'timestamp' : time(),
        'previous_hash' : previous_hash or self.hash(last_block),
        'proof' : proof
	}

    #Reset the current transactions
    self.current_transactions = []

    self.chain.append(block)
    return block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block
        :param sender: <str> Address of the Sender
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the Block that will hold this transaction
        """

        self.current_transactions.append({
            'sender' : sender,
            'recipient' : recipient,
            'amount' : amount
        })

        return len(self.chain) + 1

    @staticmethod
    def hash(block):
         """
        Creates a SHA-256 hash of a Block
        :param block: <dict> Block
        :return: <str>
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_str = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof

        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

# Instantiate App
app = Flask(__name__)

# Generate a globally unique identifier for the node
node_identifier = str(uuid4()).replace('-','')

# Instantiate Blockchain
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine:
    return "We'll mine a new block"

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    transaction_obj = request.get_json()

    required_params = ['sender', 'recipient', 'amount']
    if not all(param in transaction_obj for param in required_params):
        return 'Missing a required parameter: ' + param, 400

    block_index = blockchain.new_transaction(transaction_obj['sender'], transaction_obj['recipient'], transaction_obj['amount'])

    response = {
        'message' : f'Transaction will be added to Block {block_index}'
    }
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain:
    response = {
        'chain' : blockchain.chain,
        'length' : len(blockchain.chain)
    }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
